from __future__ import annotations

import pytest

from app.contracts import ModelTier, RoutingCapability, TaskClass
from app.errors import ConfigurationError
from app.model.router import ModelRouter
from app.settings import Settings


def _router() -> ModelRouter:
    return ModelRouter(
        settings=Settings(
            nebius_api_key="k",
            nebius_ai_project="p",
            nemotron_model_nano="model-nano",
            nemotron_model_super="model-super",
            nemotron_model_ultra="model-ultra",
        )
    )


@pytest.mark.parametrize(
    ("capability", "tier", "model"),
    [
        (RoutingCapability.EXTRACTION, ModelTier.NANO, "model-nano"),
        (RoutingCapability.CLASSIFICATION, ModelTier.NANO, "model-nano"),
        (RoutingCapability.ROUTINE_DECISION, ModelTier.NANO, "model-nano"),
        (RoutingCapability.CODING, ModelTier.SUPER, "model-super"),
        (RoutingCapability.DEBUGGING, ModelTier.SUPER, "model-super"),
        (RoutingCapability.ARCHITECTURE, ModelTier.ULTRA, "model-ultra"),
        (RoutingCapability.SYNTHESIS, ModelTier.ULTRA, "model-ultra"),
        (RoutingCapability.CERTIFICATION, ModelTier.ULTRA, "model-ultra"),
    ],
)
async def test_capability_tier_mapping(
    capability: RoutingCapability,
    tier: ModelTier,
    model: str,
) -> None:
    decision = await _router().decide(capability)
    assert decision.tier is tier
    assert decision.selected_model == model
    assert decision.capability is capability
    assert decision.task_class is TaskClass.NORMAL
    assert decision.confidence == 1.0


async def test_simple_task_downgrades_super_to_nano() -> None:
    for capability in (RoutingCapability.CODING, RoutingCapability.DEBUGGING):
        decision = await _router().decide(capability, TaskClass.SIMPLE)
        assert decision.tier is ModelTier.NANO
        assert decision.selected_model == "model-nano"


async def test_simple_task_keeps_nano_and_ultra() -> None:
    nano = await _router().decide(RoutingCapability.EXTRACTION, TaskClass.SIMPLE)
    assert nano.tier is ModelTier.NANO
    ultra = await _router().decide(RoutingCapability.ARCHITECTURE, TaskClass.SIMPLE)
    assert ultra.tier is ModelTier.ULTRA


async def test_large_context_escalates_nano_to_super() -> None:
    decision = await _router().decide(
        RoutingCapability.EXTRACTION, context_chars=400_000
    )
    assert decision.tier is ModelTier.SUPER
    assert decision.selected_model == "model-super"
    assert decision.context_tokens == 400_000 // 3


async def test_large_context_escalates_super_to_ultra() -> None:
    decision = await _router().decide(RoutingCapability.CODING, context_chars=400_000)
    assert decision.tier is ModelTier.ULTRA
    assert decision.selected_model == "model-ultra"


async def test_large_context_keeps_ultra() -> None:
    decision = await _router().decide(
        RoutingCapability.ARCHITECTURE, context_chars=400_000
    )
    assert decision.tier is ModelTier.ULTRA
    assert decision.selected_model == "model-ultra"


async def test_context_guard_boundary_at_110k_tokens() -> None:
    below = await _router().decide(
        RoutingCapability.EXTRACTION, context_chars=110_000 * 3
    )
    assert below.tier is ModelTier.NANO
    at = await _router().decide(
        RoutingCapability.EXTRACTION, context_chars=110_000 * 3 + 3
    )
    assert at.tier is ModelTier.SUPER


async def test_latency_sensitive_flag_is_recorded() -> None:
    decision = await _router().decide(
        RoutingCapability.CODING, latency_sensitive=True
    )
    assert decision.latency_sensitive is True


async def test_run_id_propagates() -> None:
    decision = await _router().decide(RoutingCapability.CODING, run_id="run-42")
    assert decision.run_id == "run-42"
    assert decision.selected_model == "model-super"


def test_model_for_tier() -> None:
    router = _router()
    assert router.model_for_tier(ModelTier.NANO) == "model-nano"
    assert router.model_for_tier(ModelTier.SUPER) == "model-super"
    assert router.model_for_tier(ModelTier.ULTRA) == "model-ultra"


def test_model_for_tier_raises_when_not_configured() -> None:
    router = ModelRouter(
        settings=Settings(nebius_api_key="k", nemotron_model_nano="  ")
    )
    with pytest.raises(ConfigurationError) as exc_info:
        router.model_for_tier(ModelTier.NANO)
    assert exc_info.value.category.value == "configuration_failure"


def test_tier_for_model_resolves_configured_ids() -> None:
    router = _router()
    assert router.tier_for_model("model-nano") is ModelTier.NANO
    assert router.tier_for_model("model-super") is ModelTier.SUPER
    assert router.tier_for_model("model-ultra") is ModelTier.ULTRA


def test_tier_for_model_resolves_tier_names() -> None:
    router = _router()
    assert router.tier_for_model("nano") is ModelTier.NANO
    assert router.tier_for_model("super") is ModelTier.SUPER
    assert router.tier_for_model("ultra") is ModelTier.ULTRA


def test_tier_for_model_returns_none_for_unknown() -> None:
    assert _router().tier_for_model("not-a-real-model") is None

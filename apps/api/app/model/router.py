from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from app.contracts import ModelTier, RoutingCapability, RoutingDecision, TaskClass
from app.errors import ConfigurationError
from app.settings import Settings, get_settings

_CHARS_PER_TOKEN: Final[int] = 3
_CONTEXT_GUARD_TOKENS: Final[int] = 110_000
_DEFAULT_TASK_CLASS: Final = TaskClass.NORMAL

_CAPABILITY_TIERS: Final[dict[RoutingCapability, ModelTier]] = {
    RoutingCapability.EXTRACTION: ModelTier.NANO,
    RoutingCapability.CLASSIFICATION: ModelTier.NANO,
    RoutingCapability.ROUTINE_DECISION: ModelTier.NANO,
    RoutingCapability.CODING: ModelTier.SUPER,
    RoutingCapability.DEBUGGING: ModelTier.SUPER,
    RoutingCapability.ARCHITECTURE: ModelTier.ULTRA,
    RoutingCapability.SYNTHESIS: ModelTier.ULTRA,
    RoutingCapability.CERTIFICATION: ModelTier.ULTRA,
}

_ESCALATION: Final[dict[ModelTier, ModelTier]] = {
    ModelTier.NANO: ModelTier.SUPER,
    ModelTier.SUPER: ModelTier.ULTRA,
}


class ModelRouter:
    """Deterministic, explainable routing from capability to a configured model tier."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings if settings is not None else get_settings()

    def model_for_tier(self, tier: ModelTier) -> str:
        """Resolve the configured model id for a tier."""
        configured: dict[ModelTier, str] = {
            ModelTier.NANO: self._settings.nemotron_model_nano,
            ModelTier.SUPER: self._settings.nemotron_model_super,
            ModelTier.ULTRA: self._settings.nemotron_model_ultra,
        }
        model = configured[tier].strip()
        if not model:
            raise ConfigurationError(
                f"No model id configured for tier {tier.value}",
                model=tier.value,
            )
        return model

    def tier_for_model(self, model: str) -> ModelTier | None:
        """Best-effort tier resolution for an explicit model id or tier name."""
        cleaned = model.strip()
        candidates: dict[str, ModelTier] = {
            self.model_for_tier(ModelTier.NANO): ModelTier.NANO,
            self.model_for_tier(ModelTier.SUPER): ModelTier.SUPER,
            self.model_for_tier(ModelTier.ULTRA): ModelTier.ULTRA,
        }
        for tier in ModelTier:
            candidates.setdefault(tier.value, tier)
        return candidates.get(cleaned)

    async def decide(
        self,
        capability: RoutingCapability,
        task_class: TaskClass | None = None,
        *,
        context_chars: int = 0,
        latency_sensitive: bool = False,
        run_id: str | None = None,
    ) -> RoutingDecision:
        """Produce a deterministic, explainable RoutingDecision for a capability."""
        task = task_class if task_class is not None else _DEFAULT_TASK_CLASS
        context_tokens = max(0, context_chars) // _CHARS_PER_TOKEN
        tier = _CAPABILITY_TIERS[capability]
        clauses: list[str] = [
            f"capability={capability.value} with task_class={task.value} "
            f"maps to tier={tier.value}"
        ]
        if task is TaskClass.SIMPLE and tier is ModelTier.SUPER:
            tier = ModelTier.NANO
            clauses.append(
                "task_class=simple keeps tier=nano despite coding-class capability"
            )
        if context_tokens > _CONTEXT_GUARD_TOKENS:
            if tier is not ModelTier.ULTRA:
                escalated = _ESCALATION[tier]
                clauses.append(
                    f"context estimated at {context_tokens} tokens exceeds "
                    f"guard of {_CONTEXT_GUARD_TOKENS}, escalating "
                    f"tier={tier.value} -> tier={escalated.value}"
                )
                tier = escalated
            else:
                clauses.append(
                    "context exceeds guard but tier=ultra already assigned; no escalation"
                )
        if latency_sensitive:
            if tier in (ModelTier.SUPER, ModelTier.ULTRA):
                clauses.append(
                    f"latency-sensitive: tier={tier.value} kept as-is; "
                    "latency/cost tradeoff accepted"
                )
            else:
                clauses.append(
                    "latency-sensitive: tier=nano is lowest-latency; no tradeoff"
                )
        model = self.model_for_tier(tier)
        clauses.append(f"selected_model={model}")
        return RoutingDecision(
            selected_model=model,
            tier=tier,
            reason="; ".join(clauses),
            task_class=task,
            capability=capability,
            confidence=1.0,
            context_tokens=context_tokens,
            latency_sensitive=latency_sensitive,
            criticality="normal",
            timestamp=datetime.now(UTC),
            run_id=run_id,
        )

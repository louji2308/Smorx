from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from app.contracts import (
    ModelCompletion,
    ModelRequest,
    ModelResponse,
    ModelTier,
    ProviderHealthReport,
    RoutingCapability,
    RoutingDecision,
    TaskClass,
)
from app.errors import ConfigurationError
from app.model.router import _CHARS_PER_TOKEN, _CONTEXT_GUARD_TOKENS, ModelRouter
from app.observability import TraceContext, trace_operation
from app.settings import Settings


@runtime_checkable
class TokenFactoryClient(Protocol):
    """Minimal contract the model service depends on from the Token Factory client."""

    async def chat_completion(self, request: ModelRequest) -> ModelResponse: ...

    async def health(self) -> ProviderHealthReport: ...


def _parse_capability(model: str) -> RoutingCapability | None:
    try:
        return RoutingCapability(model)
    except ValueError:
        return None


class NemotronModelService:
    """Model adapter that routes requests and runs them through the real provider client."""

    def __init__(
        self,
        client: TokenFactoryClient,
        router: ModelRouter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._client = client
        self._router = router if router is not None else ModelRouter(settings=settings)

    async def complete(self, request: ModelRequest) -> ModelCompletion:
        """Route a request, run it through the provider, and bind the routing decision."""
        decision = await self._decide_routing(request)
        target = request.model_copy(update={"model": decision.selected_model})
        trace_ctx = TraceContext(request_id=request.request_id)
        if request.run_id:
            trace_ctx.run_id = request.run_id
        with trace_operation(
            "model_completion",
            trace_ctx,
            provider="nebius_token_factory",
            model=decision.selected_model,
        ):
            response = await self._client.chat_completion(target)
        return ModelCompletion(response=response, routing=decision)

    async def health(self) -> ProviderHealthReport:
        """Delegate provider health to the Token Factory client."""
        trace_ctx = TraceContext()
        with trace_operation(
            "model_provider_health",
            trace_ctx,
            provider="nebius_token_factory",
        ):
            return await self._client.health()

    async def _decide_routing(self, request: ModelRequest) -> RoutingDecision:
        raw = request.model.strip()
        if not raw:
            raise ConfigurationError(
                "ModelRequest.model is empty; cannot derive model routing",
                request_id=request.request_id,
                run_id=request.run_id,
            )
        capability = _parse_capability(raw)
        context_chars = len(request.prompt) + len(request.system or "")
        if capability is not None:
            return await self._router.decide(
                capability,
                context_chars=context_chars,
                run_id=request.run_id,
            )
        tier = self._router.tier_for_model(raw)
        if tier is None:
            raise ConfigurationError(
                f"ModelRequest.model {raw!r} does not name a supported model id, "
                "tier, or routing capability; cannot derive model routing",
                request_id=request.request_id,
                run_id=request.run_id,
            )
        return self._explicit_decision(tier, raw, context_chars, request.run_id)

    def _explicit_decision(
        self,
        tier: ModelTier,
        raw: str,
        context_chars: int,
        run_id: str | None,
    ) -> RoutingDecision:
        model = self._router.model_for_tier(tier)
        context_tokens = max(0, context_chars) // _CHARS_PER_TOKEN
        clauses: list[str] = [
            f"explicit request {raw!r} bound to tier={tier.value} (model {model})",
            "capability and task_class not declared; recorded as "
            "routine_decision/normal for traceability",
        ]
        if context_tokens > _CONTEXT_GUARD_TOKENS:
            clauses.append(
                f"context estimated at {context_tokens} tokens exceeds guard of "
                f"{_CONTEXT_GUARD_TOKENS} but explicit model was honored (no escalation)"
            )
        return RoutingDecision(
            selected_model=model,
            tier=tier,
            reason="; ".join(clauses),
            task_class=TaskClass.NORMAL,
            capability=RoutingCapability.ROUTINE_DECISION,
            confidence=1.0,
            context_tokens=context_tokens,
            latency_sensitive=False,
            criticality="normal",
            timestamp=datetime.now(UTC),
            run_id=run_id,
        )

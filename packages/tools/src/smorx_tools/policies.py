"""Risk/approval policy contracts and the deterministic policy engine.

Phase 4 ``smorx_tools.policies``: risk levels, policy decisions, resource
kinds, the immutable evaluation context (:class:`PolicyContext`), explicit
first-match :class:`PolicyRule` objects, and :class:`PolicyEngine`, the
deterministic engine the control plane consults on every authorization.

Evaluation is intentionally deterministic:

* Explicit rules are consulted first, in rule order, and the *first matching
  rule* wins (see :meth:`PolicyEngine.evaluate_with_rules` for exact matching
  semantics).
* When no rule matches, the risk-based :data:`DEFAULT_RISK_POLICY` is used:
  LOW/MEDIUM -> ``ALLOW``, HIGH -> ``REQUIRE_REVIEW``, CRITICAL -> ``BLOCK``.
  This risk policy is environment-independent on purpose: HIGH risk always
  requires review wherever the tool runs.
* ``production_requires_approval=True`` (the default) additionally promotes a
  default-derived ``ALLOW`` for MEDIUM or HIGH risk in the ``production``
  environment to ``REQUIRE_REVIEW``, unless an explicit rule already allowed
  the context (an explicit `ALLOW` rule never gets promoted).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType


class RiskLevel(StrEnum):
    """Severity of the operation a tool performs."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecision(StrEnum):
    """Deterministic disposition returned by the policy engine."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_REVIEW = "REQUIRE_REVIEW"
    BLOCK = "BLOCK"


class ResourceKind(StrEnum):
    """Kind of resource an authorization targets, for resource-scoped rules."""

    TOOL = "TOOL"
    PATH = "PATH"
    FILE = "FILE"
    COMMAND = "COMMAND"
    DATABASE = "DATABASE"
    NETWORK = "NETWORK"
    ENVIRONMENT = "ENVIRONMENT"
    SANDBOX = "SANDBOX"
    SECRET = "SECRET"


DEFAULT_RISK_POLICY: Mapping[RiskLevel, PolicyDecision] = {
    RiskLevel.LOW: PolicyDecision.ALLOW,
    RiskLevel.MEDIUM: PolicyDecision.ALLOW,
    RiskLevel.HIGH: PolicyDecision.REQUIRE_REVIEW,
    RiskLevel.CRITICAL: PolicyDecision.BLOCK,
}


@dataclass(frozen=True)
class PolicyContext:
    """Immutable context evaluated by the policy engine.

    ``extra`` is defensively snapshotted into a read-only mapping on
    construction so a rule predicate can never observe later mutation.
    """

    environment: str
    agent_id: str = ""
    task_id: str = ""
    tool_name: str = ""
    risk: RiskLevel = RiskLevel.LOW
    resource: ResourceKind = ResourceKind.TOOL
    resource_ref: str = ""
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True)
class PolicyRule:
    """One explicit, first-match policy rule.

    Matching semantics (all conditions must hold):

    * ``environment`` (when non-empty): the context environment must equal it.
    * If ``tool_name`` is non-empty, the context tool name must equal it
      (a *tool-scoped* rule; ``resource`` is not consulted so a rule targeting
      one specific tool can never be silently skipped because of a resource
      mismatch).
    * If ``tool_name`` is empty, the context resource kind must equal
      ``resource`` (a *resource-scoped* rule).
    * ``predicate(ctx)`` must return ``True`` (default: always matches).
    """

    id: str
    decision: PolicyDecision
    resource: ResourceKind = ResourceKind.TOOL
    tool_name: str = ""
    environment: str = ""
    reason: str = ""
    predicate: Callable[[PolicyContext], bool] = lambda ctx: True


class PolicyEngine:
    """Deterministic, first-match policy engine over explicit rules + risk defaults.

    ``default_risk_policy`` overrides :data:`DEFAULT_RISK_POLICY` for selected
    risk levels; missing levels fall back to the module default.
    """

    def __init__(
        self,
        *,
        rules: Sequence[PolicyRule] = (),
        default_risk_policy: Mapping[RiskLevel, PolicyDecision] | None = None,
        production_requires_approval: bool = True,
    ) -> None:
        self._rules: tuple[PolicyRule, ...] = tuple(rules)
        self._default_risk_policy: dict[RiskLevel, PolicyDecision] = dict(
            default_risk_policy if default_risk_policy is not None else DEFAULT_RISK_POLICY
        )
        self._production_requires_approval: bool = production_requires_approval

    def evaluate(self, ctx: PolicyContext) -> PolicyDecision:
        """Resolve ``ctx`` against the engine's configured rules, else defaults."""
        return self.evaluate_with_rules(ctx, self._rules)

    def evaluate_with_rules(
        self, ctx: PolicyContext, rules: Sequence[PolicyRule]
    ) -> PolicyDecision:
        """Resolve ``ctx`` against ``rules`` (first match wins), else defaults.

        Production promotion: when ``production_requires_approval`` is True, a
        default-derived ``ALLOW`` in the ``production`` environment for MEDIUM
        or HIGH risk is promoted to ``REQUIRE_REVIEW``. An explicit rule that
        ALLOWs the context returns first and is never promoted.
        """
        for rule in rules:
            if self._matches(rule, ctx):
                return rule.decision
        decision = self._default_decision(ctx)
        if (
            self._production_requires_approval
            and ctx.environment == "production"
            and decision is PolicyDecision.ALLOW
            and ctx.risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)
        ):
            return PolicyDecision.REQUIRE_REVIEW
        return decision

    def default_risk_policy(self) -> Mapping[RiskLevel, PolicyDecision]:
        """Read-only view of the risk->decision mapping in effect."""
        return MappingProxyType(dict(self._default_risk_policy))

    def _default_decision(self, ctx: PolicyContext) -> PolicyDecision:
        return self._default_risk_policy.get(ctx.risk, DEFAULT_RISK_POLICY[ctx.risk])

    def _matches(self, rule: PolicyRule, ctx: PolicyContext) -> bool:
        if rule.environment and rule.environment != ctx.environment:
            return False
        if rule.tool_name:
            if rule.tool_name != ctx.tool_name:
                return False
        elif rule.resource is not ctx.resource:
            return False
        return rule.predicate(ctx)

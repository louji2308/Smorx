"""Agent coordinator contracts for the parallel multi-agent runtime.

Dataclasses capturing one assignment of work to a specialized sub-agent and
the evidence-bearing result it must return.  The two discipline functions
implement the project invariants "no evidence, no success" and "every
consequential mutation is attributable":

* :func:`validate_result` refuses to certify a SUCCEEDED agent that returned
  neither evidence nor an execution reference, and a FAILED agent without a
  failure record.
* :func:`assignment_allows_tool` enforces that sub-agents may only reach tools
  permitted by their assignment's ``allowed_tools`` (exact names or dotted
  prefixes).

Designed for ``IMPLEMENTATION_PLAN.md`` phase 3: the orchestrator hands
:class:`AgentAssignment` objects to :class:`AgentExecutor` implementations it
creates through :class:`AgentExecutorFactory`; :class:`AgentResult` is the
contract for everything an executor reports back.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Literal, Protocol, TypeVar, runtime_checkable

from smorx_runtime.capabilities import SpecialistCapability

K = TypeVar("K")
V = TypeVar("V")


def _frozen_mapping(value: Mapping[K, V]) -> Mapping[K, V]:
    """Return a defensive immutable snapshot of ``value``."""
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class AgentContext:
    """Immutable execution context shared by every agent in one run."""

    run_id: str
    phase: str
    task_id: str
    correlation_id: str
    repository: str = ""
    change_id: str = ""
    environment: Mapping[str, str] = field(default_factory=dict)
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "environment", _frozen_mapping(self.environment))
        object.__setattr__(self, "extra", _frozen_mapping(self.extra))


@dataclass(frozen=True)
class AgentAssignment:
    """One unit of work delegated by the orchestrator to a sub-agent."""

    id: str
    task_id: str
    wave_id: str
    agent_id: str
    objective: str
    capability: SpecialistCapability
    context: AgentContext
    inputs: Mapping[str, object]
    constraints: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    expected_artifact: str
    timeout_seconds: float
    created_at: datetime


@dataclass(frozen=True)
class AgentEvidence:
    """One piece of machine-observable execution evidence produced by an agent."""

    evidence_id: str
    source: str
    timestamp: datetime
    evidence_type: str = "EXECUTION_RESULT"
    claim_id: str | None = None
    machine_result: Mapping[str, object] = field(default_factory=dict)
    provenance: str = ""
    related_execution: str = ""


@dataclass(frozen=True)
class AgentFailure:
    """A classified failure with enough information to drive the next decision."""

    failure_id: str
    classification: str
    summary: str
    observed_at: datetime
    evidence: str = ""
    probable_cause: str = ""
    next_action: str = ""


@dataclass(frozen=True)
class AgentResult:
    """The evidence-bearing contract every executor must return."""

    assignment_id: str
    task_id: str
    status: Literal["SUCCEEDED", "FAILED", "BLOCKED"]
    started_at: datetime
    finished_at: datetime
    claims: tuple[str, ...] = ()
    artifacts: Mapping[str, object] = field(default_factory=dict)
    evidence: tuple[AgentEvidence, ...] = ()
    failures: tuple[AgentFailure, ...] = ()
    execution_references: tuple[str, ...] = ()
    confidence: float = 0.0
    next_recommendation: str = ""
    summary: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be within [0, 1], got {self.confidence}")


@dataclass(frozen=True)
class AgentSpec:
    """Static description of a specialist the orchestrator may instantiate."""

    agent_id: str
    name: str
    capability: SpecialistCapability
    replacement_weight: int = 1


@runtime_checkable
class AgentExecutor(Protocol):
    """A sub-agent that can execute one :class:`AgentAssignment`."""

    async def execute(self, assignment: AgentAssignment) -> AgentResult: ...


@runtime_checkable
class AgentExecutorFactory(Protocol):
    """Creates :class:`AgentExecutor` instances for a specialist spec."""

    def create(self, spec: AgentSpec, *, allowed_tools: tuple[str, ...]) -> AgentExecutor: ...


def validate_result(result: AgentResult) -> tuple[str, ...]:
    """Return discipline-issue strings for a result; empty when it is valid.

    Objective discipline ("no evidence, no success", ``Requirements &
    Contract.md`` section 3):

    * a SUCCEEDED result must carry at least one evidence entry or at least
      one execution reference;
    * a SUCCEEDED result must not carry failures;
    * a FAILED result must carry at least one failure record;
    * confidence must lie within ``[0, 1]`` (also enforced at construction);
    * ``finished_at`` must not precede ``started_at``.
    """
    issues: list[str] = []
    if result.status == "SUCCEEDED":
        if not result.evidence and not result.execution_references:
            issues.append("SUCCEEDED without evidence")
        if result.failures:
            issues.append("SUCCEEDED with failures")
    elif result.status == "FAILED":
        if not result.failures:
            issues.append("FAILED without failure record")
    if not 0.0 <= result.confidence <= 1.0:
        issues.append("confidence out of range")
    if result.finished_at < result.started_at:
        issues.append("finished_at before started_at")
    return tuple(issues)


def assignment_allows_tool(assignment: AgentAssignment, tool_name: str) -> bool:
    """Whether ``tool_name`` is permitted by the assignment's allowed tools.

    An allowed entry matches the exact tool name or acts as a dotted prefix:
    ``"file."`` permits ``file.read`` and ``file.write``, while ``"command.run"``
    matches only ``command.run`` itself.
    """
    for entry in assignment.allowed_tools:
        if tool_name == entry:
            return True
        if entry.endswith(".") and tool_name.startswith(entry):
            return True
    return False

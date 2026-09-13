"""Core contracts for the policy-controlled tool layer.

Defines the tool taxonomy (:class:`ToolKind`), the result-status vocabulary
(:class:`ToolResultStatus`), the immutable request and execution-record
dataclasses (:class:`ToolRequest`, :class:`ToolExecutionResult`), the tool
manifest (:class:`ToolSpec`), and the capability-scoped
:class:`ToolRegistry`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType


class ToolKind(StrEnum):
    """Taxonomy of tool kinds the control plane can gate."""

    REPOSITORY = "REPOSITORY"
    FILE = "FILE"
    COMMAND = "COMMAND"
    TEST = "TEST"
    SANDBOX = "SANDBOX"
    VERIFICATION = "VERIFICATION"
    MODEL = "MODEL"
    POLICY = "POLICY"
    CONTROL = "CONTROL"


class ToolResultStatus(StrEnum):
    """Vocabulary of tool invocation outcomes."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
    DENIED = "DENIED"
    BLOCKED = "BLOCKED"
    PENDING_REVIEW = "PENDING_REVIEW"
    UNAVAILABLE = "UNAVAILABLE"


def is_success(status: ToolResultStatus) -> bool:
    """Return whether ``status`` counts as an unqualified success.

    Only ``SUCCEEDED`` is success. Every other status -- including
    ``PENDING_REVIEW`` and ``FAILED`` -- is not.
    """
    return status == ToolResultStatus.SUCCEEDED


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ToolSpec:
    """Static manifest of one tool: identity, risk, routing, approval, handler."""

    name: str
    kind: ToolKind
    description: str
    capability: str
    risk: str = "low"
    timeout_seconds: float = 30.0
    requires_sandbox: bool = False
    mutates: bool = False
    requires_approval: bool = False
    handler: Callable[[ToolRequest], Awaitable[ToolExecutionResult]] | None = None


@dataclass(frozen=True)
class ToolRequest:
    """Immutable invocation request; arguments are snapshotted on construction."""

    request_id: str
    action_id: str
    agent_id: str
    task_id: str
    tool_name: str
    arguments: Mapping[str, object]
    assignment_capabilities: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    phase: str = ""
    environment: str = "development"
    timeout_seconds: float = 30.0
    sandbox_id: str = ""
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))


@dataclass(frozen=True)
class ToolExecutionResult:
    """Immutable execution record binding an outcome to its provenance."""

    invocation_id: str
    tool_name: str
    request_id: str
    status: ToolResultStatus
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    artifacts: Mapping[str, object] = field(default_factory=dict)
    error_classification: str = ""
    timeout_seconds: float = 0.0
    sandbox_id: str = ""
    provenance: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", MappingProxyType(dict(self.artifacts)))


class ToolRegistry:
    """Insertion-ordered, capability-routed registry of tool manifests."""

    def __init__(self) -> None:
        self._specs: list[ToolSpec] = []
        self._by_name: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """Register ``spec``; a duplicate ``name`` raises :class:`ValueError`."""
        if spec.name in self._by_name:
            raise ValueError(f"tool already registered: {spec.name}")
        self._by_name[spec.name] = spec
        self._specs.append(spec)

    def get(self, name: str) -> ToolSpec | None:
        return self._by_name.get(name)

    def names(self) -> tuple[str, ...]:
        """Return registered names in insertion order."""
        return tuple(spec.name for spec in self._specs)

    def tools_for_capability(self, capability: str) -> tuple[ToolSpec, ...]:
        """Return specs whose capability matches; ``"*"`` tools are always included."""
        return tuple(
            spec for spec in self._specs if spec.capability == "*" or spec.capability == capability
        )

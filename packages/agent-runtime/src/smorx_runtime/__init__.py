"""smorx_runtime: agent state machine, bounded execution-loop controls,
dependency-aware parallel orchestration, and the tool-authorization gateway.

Phase 3 factories:

* :mod:`smorx_runtime.capabilities` -- the nine specialist roles and the tool
  prefixes each role may use.
* :mod:`smorx_runtime.agents` -- assignment/result contracts and the
  "no evidence, no success" result validation.
* :mod:`smorx_runtime.graph` -- dependency-aware task graph with deterministic
  wave planning (``SERIALIZED`` tasks run alone).
* :mod:`smorx_runtime.waves` / :mod:`smorx_runtime.telemetry` -- real concurrent
  wave execution with timing evidence that can *prove* parallelism.
* :mod:`smorx_runtime.toolgate` -- the :class:`CapabilityGateway` seam and its
  Phase-3 enforcement double (:class:`MemoryGateway`).
* :mod:`smorx_runtime.orchestrator` -- the dependency-aware orchestrator with
  bounded retry/replacement, conflict detection, and block-on-no-progress.
"""

from smorx_runtime.agents import (
    AgentAssignment,
    AgentContext,
    AgentEvidence,
    AgentExecutor,
    AgentExecutorFactory,
    AgentFailure,
    AgentResult,
    AgentSpec,
    assignment_allows_tool,
    validate_result,
)
from smorx_runtime.capabilities import (
    CAPABILITY_CATALOG,
    AgentCapability,
    SpecialistCapability,
    capabilities_for_phase,
    capability_for,
)
from smorx_runtime.graph import (
    TaskGraph,
    TaskGraphError,
    TaskKind,
    TaskSpec,
)
from smorx_runtime.loop_controls import (
    LOOP_ENV_PREFIX,
    IterationBudget,
    LoopControlError,
    LoopControls,
    NoProgressDetector,
)
from smorx_runtime.orchestrator import (
    WORKFLOW_TRANSITIONS,
    Contradiction,
    InvalidWorkflowTransition,
    OrchestrationBlocked,
    OrchestrationDecision,
    OrchestrationReport,
    Orchestrator,
    OrchestratorConfig,
    OrchestratorState,
    RetryPolicy,
    WorkflowPhase,
)
from smorx_runtime.state import (
    TRANSITIONS,
    AgentState,
    AgentStateMachine,
    InvalidTransitionError,
    TransitionRecord,
)
from smorx_runtime.telemetry import (
    ParallelismTelemetry,
    TaskTiming,
    WaveTelemetry,
    overlap_seconds,
)
from smorx_runtime.toolgate import (
    CapabilityGateway,
    MemoryGateway,
    ToolAuthorization,
    ToolDecision,
    ToolExecutionError,
    ToolOutcome,
    UnauthorizedToolError,
)
from smorx_runtime.waves import (
    ParallelWaveEngine,
    WaveResult,
    WaveRunRequest,
    WaveStatus,
)

__all__ = [
    "CAPABILITY_CATALOG",
    "LOOP_ENV_PREFIX",
    "TRANSITIONS",
    "WORKFLOW_TRANSITIONS",
    "AgentAssignment",
    "AgentCapability",
    "AgentContext",
    "AgentEvidence",
    "AgentExecutor",
    "AgentExecutorFactory",
    "AgentFailure",
    "AgentResult",
    "AgentSpec",
    "AgentState",
    "AgentStateMachine",
    "CapabilityGateway",
    "Contradiction",
    "InvalidTransitionError",
    "InvalidWorkflowTransition",
    "IterationBudget",
    "LoopControlError",
    "LoopControls",
    "MemoryGateway",
    "NoProgressDetector",
    "OrchestrationBlocked",
    "OrchestrationDecision",
    "OrchestrationReport",
    "Orchestrator",
    "OrchestratorConfig",
    "OrchestratorState",
    "ParallelWaveEngine",
    "ParallelismTelemetry",
    "RetryPolicy",
    "SpecialistCapability",
    "TaskGraph",
    "TaskGraphError",
    "TaskKind",
    "TaskSpec",
    "TaskTiming",
    "ToolAuthorization",
    "ToolDecision",
    "ToolExecutionError",
    "ToolOutcome",
    "TransitionRecord",
    "UnauthorizedToolError",
    "WaveResult",
    "WaveRunRequest",
    "WaveStatus",
    "WaveTelemetry",
    "WorkflowPhase",
    "assignment_allows_tool",
    "capabilities_for_phase",
    "capability_for",
    "overlap_seconds",
    "validate_result",
]

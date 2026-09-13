"""smorx_tools: policy-controlled tool layer for the agent runtime.

Phase 4 of ``IMPLEMENTATION_PLAN.md``: the registry of real tools, the risk
policy engine, the append-only audit trail, the sandbox / human / repository
ports, and the :class:`~smorx_tools.control.ControlPlane` gateway that
implements ``smorx_runtime.toolgate.CapabilityGateway``.

The orchestrator assembly (:mod:`smorx_tools.assembly`) binds the default
registry over a repository root; later phases bind a real Nebius sandbox
provider through :class:`~smorx_tools.sandbox.SandboxControl`.
"""

from smorx_tools.assembly import assemble_control_plane, assemble_default_registry
from smorx_tools.audit import AuditDecision, AuditRecord, AuditTrail
from smorx_tools.control import ApprovalGate, ControlPlane
from smorx_tools.execution import (
    CommandResult,
    CommandRunner,
    ExecutionError,
    FailureClassifier,
    normalize_test_output,
)
from smorx_tools.human import (
    ApprovalError,
    ApprovalRequest,
    ApprovalStatus,
    ControlState,
    HumanControlPlane,
)
from smorx_tools.policies import (
    DEFAULT_RISK_POLICY,
    PolicyContext,
    PolicyDecision,
    PolicyEngine,
    PolicyRule,
    ResourceKind,
    RiskLevel,
)
from smorx_tools.repo import PathSafety, PathSafetyError, RepositoryToolkit
from smorx_tools.sandbox import (
    SandboxCapability,
    SandboxControl,
    SandboxOperationResult,
    SandboxPort,
    SandboxStatus,
)
from smorx_tools.tool import (
    ToolExecutionResult,
    ToolKind,
    ToolRegistry,
    ToolRequest,
    ToolResultStatus,
    ToolSpec,
    is_success,
)

__all__ = [
    "DEFAULT_RISK_POLICY",
    "ApprovalError",
    "ApprovalGate",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditDecision",
    "AuditRecord",
    "AuditTrail",
    "CommandResult",
    "CommandRunner",
    "ControlPlane",
    "ControlState",
    "ExecutionError",
    "FailureClassifier",
    "HumanControlPlane",
    "PathSafety",
    "PathSafetyError",
    "PolicyContext",
    "PolicyDecision",
    "PolicyEngine",
    "PolicyRule",
    "RepositoryToolkit",
    "ResourceKind",
    "RiskLevel",
    "SandboxCapability",
    "SandboxControl",
    "SandboxOperationResult",
    "SandboxPort",
    "SandboxStatus",
    "ToolExecutionResult",
    "ToolKind",
    "ToolRegistry",
    "ToolRequest",
    "ToolResultStatus",
    "ToolSpec",
    "assemble_control_plane",
    "assemble_default_registry",
    "is_success",
    "normalize_test_output",
]

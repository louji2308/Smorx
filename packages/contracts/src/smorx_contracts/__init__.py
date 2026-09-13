"""smorx_contracts — master contracts, registry, versioning, and events.

Standalone import surface (no app packages required):

- ``CONTRACT_NAMES`` — exactly the 17 master contracts, in registry order.
- ``get_registry()`` — singleton ``ContractRegistry``.
- ``validate_contract(name, obj)`` — registry validation (bool, raises on failure).
- ``sample_instance(name)`` — minimal valid demo/seed instance per contract.
- ``ConsequentialEvent`` — §2.4 structured evidence event model.
- ``*.validate_version``, ``*.bump_*``, ``*.is_compatible``, ``*.immutable_key``
  versioning helpers (ADR-0005).
"""

from __future__ import annotations

from typing import Any

from . import models, registry, versioning
from .models import (
    CONTRACT_NAMES,
    EVENT_TYPES,
    Action,
    AgentRun,
    BehavioralDelta,
    BehavioralObject,
    CandidatePatch,
    Certificate,
    Claim,
    ConsequentialEvent,
    Evidence,
    ExecutionResult,
    Failure,
    Intent,
    PhaseGate,
    RepairPackage,
    SubagentRun,
    Task,
    ToolInvocation,
    VerificationPlan,
    VersionedModel,
)
from .registry import (
    ContractError,
    ContractRegistry,
    ContractValidationError,
    UnknownContractError,
    get_registry,
    sample_instance,
)
from .versioning import (
    bump_major,
    bump_minor,
    bump_patch,
    immutable_key,
    is_compatible,
    validate_version,
)

__all__ = [
    "CONTRACT_NAMES",
    "EVENT_TYPES",
    "Action",
    "AgentRun",
    "BehavioralDelta",
    "BehavioralObject",
    "CandidatePatch",
    "Certificate",
    "Claim",
    "ConsequentialEvent",
    "ContractError",
    "ContractRegistry",
    "ContractValidationError",
    "Evidence",
    "ExecutionResult",
    "Failure",
    "Intent",
    "PhaseGate",
    "RepairPackage",
    "SubagentRun",
    "Task",
    "ToolInvocation",
    "UnknownContractError",
    "VerificationPlan",
    "VersionedModel",
    "bump_major",
    "bump_minor",
    "bump_patch",
    "get_registry",
    "immutable_key",
    "is_compatible",
    "models",
    "registry",
    "sample_instance",
    "validate_contract",
    "validate_version",
    "versioning",
]


def validate_contract(name: str, obj: Any) -> bool:
    """Validate ``obj`` against the named contract.

    Returns ``True``; raises ``UnknownContractError`` for unknown names and
    ``ContractValidationError`` for invalid instances or failed cross-refs.
    """
    return get_registry().validate(name, obj)

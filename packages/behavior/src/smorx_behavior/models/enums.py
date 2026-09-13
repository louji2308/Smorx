"""Canonical enum values for the behavioral data model.

These values MUST stay synchronized with ``smorx_contracts`` (the JSON
Schema ``enum`` arrays owned by the contracts agent). Do not add members
casually: every member represents a machine-validated vocabulary used by
the evidence chain and certification binding.
"""

from __future__ import annotations

from enum import StrEnum


class EvidenceType(StrEnum):
    """Classification of a single evidence object (implementation plan 2.2)."""

    STATIC_ANALYSIS = "STATIC_ANALYSIS"
    DIFFERENTIAL_EXECUTION = "DIFFERENTIAL_EXECUTION"
    HISTORICAL_GHOST_REPLAY = "HISTORICAL_GHOST_REPLAY"
    METAMORPHIC_CHECK = "METAMORPHIC_CHECK"
    ADVERSARIAL_SCENARIO = "ADVERSARIAL_SCENARIO"
    MUTATION_TEST = "MUTATION_TEST"
    EXECUTION_TRACE = "EXECUTION_TRACE"
    TEST_RESULT = "TEST_RESULT"
    RUNTIME_OBSERVATION = "RUNTIME_OBSERVATION"
    REPOSITORY_SNAPSHOT = "REPOSITORY_SNAPSHOT"
    MODEL_DECISION = "MODEL_DECISION"
    CERTIFICATE_BINDING = "CERTIFICATE_BINDING"


class LockState(StrEnum):
    """Immutable-reference lock state (versioning/immutability contract)."""

    UNLOCKED = "UNLOCKED"
    LOCKED = "LOCKED"


class EventKind(StrEnum):
    """Structured categories for the consequential event pipeline."""

    TASK_RECEIVED = "TASK_RECEIVED"
    REPOSITORY_INSPECTED = "REPOSITORY_INSPECTED"
    PLAN_GENERATED = "PLAN_GENERATED"
    SANDBOX_CREATED = "SANDBOX_CREATED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    RESULT_OBSERVED = "RESULT_OBSERVED"
    FAILURE_CLASSIFIED = "FAILURE_CLASSIFIED"
    PATCH_GENERATED = "PATCH_GENERATED"
    EVIDENCE_RECORDED = "EVIDENCE_RECORDED"
    VERIFICATION_RUN = "VERIFICATION_RUN"
    BEHAVIORAL_DELTA = "BEHAVIORAL_DELTA"
    INTENT_ALIGNMENT = "INTENT_ALIGNMENT"
    REPAIR = "REPAIR"
    REVERIFICATION = "REVERIFICATION"
    CERTIFICATION = "CERTIFICATION"
    MEMORY_UPDATE = "MEMORY_UPDATE"
    MERGE = "MERGE"
    BLOCKED = "BLOCKED"


class RunStatus(StrEnum):
    """Lifecycle of a run/agent run (documented minimal extension)."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class CertificateStatus(StrEnum):
    """Lifecycle of a certificate (documented minimal extension)."""

    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    CERTIFIED = "CERTIFIED"
    REVOKED = "REVOKED"


class IntentAlignmentStatus(StrEnum):
    """Alignment verdict for an intent item (documented minimal extension)."""

    PENDING = "PENDING"
    ALIGNED = "ALIGNED"
    MISALIGNED = "MISALIGNED"


class FailureKind(StrEnum):
    """Failure taxonomy from ``Requirements & Contract.md`` section 9 (F1-F10)."""

    F1_SYNTAX_BUILD = "F1_SYNTAX_BUILD"
    F2_UNIT_TEST = "F2_UNIT_TEST"
    F3_INTEGRATION = "F3_INTEGRATION"
    F4_ENVIRONMENT_DEPENDENCY = "F4_ENVIRONMENT_DEPENDENCY"
    F5_TIMEOUT = "F5_TIMEOUT"
    F6_PERMISSION = "F6_PERMISSION"
    F7_TOOL = "F7_TOOL"
    F8_AMBIGUOUS_RESULT = "F8_AMBIGUOUS_RESULT"
    F9_ACCEPTANCE_CRITERION = "F9_ACCEPTANCE_CRITERION"
    F10_SAFETY_POLICY_BLOCK = "F10_SAFETY_POLICY_BLOCK"


class RepairStatus(StrEnum):
    """Lifecycle of a repair package (documented minimal extension)."""

    CREATED = "CREATED"
    APPLIED = "APPLIED"
    REVERIFIED = "REVERIFIED"
    FAILED = "FAILED"
    REVERTED = "REVERTED"
    BLOCKED = "BLOCKED"


class AgentState(StrEnum):
    """Agent lifecycle state machine (implementation plan section 11)."""

    CREATED = "CREATED"
    INSPECTED = "INSPECTED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    OBSERVED = "OBSERVED"
    FAILED = "FAILED"
    ITERATING = "ITERATING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"


class TaskStatus(StrEnum):
    """Lifecycle of a task inside the governed lifecycle."""

    CREATED = "CREATED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    MERGED = "MERGED"


class Priority(StrEnum):
    """Priority assigned to a task or intent item."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Severity(StrEnum):
    """Severity shared by invariants, incidents, risk zones, and failures."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DeltaDirection(StrEnum):
    """Direction of an observed behavioral difference (implementation plan 18)."""

    INCREASED = "INCREASED"
    DECREASED = "DECREASED"
    UNCHANGED = "UNCHANGED"
    MIXED = "MIXED"


class ClaimStatus(StrEnum):
    """Evidence-backed state of a claim."""

    OPEN = "OPEN"
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    VERIFIED = "VERIFIED"


class ConstitutionStatus(StrEnum):
    """Lifecycle of a behavioral constitution."""

    DRAFT = "DRAFT"
    RATIFIED = "RATIFIED"
    SUPERSEDED = "SUPERSEDED"


class IntentStatus(StrEnum):
    """Lifecycle of an intent ledger or intent item."""

    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"


class IntentKind(StrEnum):
    """Kind of intent item recorded by the intent ledger."""

    REQUIREMENT = "REQUIREMENT"
    CONSTRAINT = "CONSTRAINT"
    ACCEPTANCE_CRITERION = "ACCEPTANCE_CRITERION"


class VerificationStatus(StrEnum):
    """Lifecycle of a verification case or execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


class MemoryKind(StrEnum):
    """Category of a behavioral memory update."""

    BEHAVIORAL_MEMORY = "BEHAVIORAL_MEMORY"
    FAILURE_ARCHAEOLOGY = "FAILURE_ARCHAEOLOGY"
    CERTIFICATION = "CERTIFICATION"
    GOVERNANCE = "GOVERNANCE"

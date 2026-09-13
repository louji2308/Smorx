"""Pydantic v2 runtime models for the 17 master contracts (ADR-0002).

Field shapes and enum vocabularies are synchronized with the JSON Schemas in
``packages/contracts/schemas/`` (the cross-language source of truth). The
registry tests assert schema/model drift is zero. All 17 contracts share
``VersionedModel`` (id + semver ``version``, ADR-0005) and forbid unknown
fields so contract drift fails fast at validation time.

The supplementary ``ConsequentialEvent`` model implements the §2.4 structured
event schema and is intentionally NOT one of the 17 master contracts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import versioning

CONTRACT_NAMES: tuple[str, ...] = (
    "task",
    "action",
    "tool_invocation",
    "execution_result",
    "failure",
    "evidence",
    "claim",
    "behavioral_object",
    "intent",
    "verification_plan",
    "candidate_patch",
    "behavioral_delta",
    "repair_package",
    "certificate",
    "agent_run",
    "subagent_run",
    "phase_gate",
)

EVENT_TYPES: tuple[str, ...] = (
    "TASK_RECEIVED",
    "REPOSITORY_INSPECTED",
    "PLAN_GENERATED",
    "SANDBOX_CREATED",
    "ACTION_EXECUTED",
    "RESULT_OBSERVED",
    "FAILURE_CLASSIFIED",
    "PATCH_GENERATED",
    "EVIDENCE_RECORDED",
    "VERIFICATION_RUN",
    "BEHAVIORAL_DELTA",
    "INTENT_ALIGNMENT",
    "REPAIR",
    "REVERIFICATION",
    "CERTIFICATION",
    "MEMORY_UPDATE",
    "MERGE",
    "BLOCKED",
)

# -- Shared vocabulary (also declared as enum arrays in the JSON Schemas) ------

FailureClassification = Literal[
    "syntax/build failure",
    "unit-test failure",
    "integration failure",
    "environment/dependency failure",
    "timeout",
    "permission failure",
    "tool failure",
    "ambiguous result",
    "acceptance-criterion failure",
    "safety/policy block",
]

EvidenceType = Literal[
    "STATIC_ANALYSIS",
    "DIFFERENTIAL_EXECUTION",
    "HISTORICAL_GHOST_REPLAY",
    "METAMORPHIC_CHECK",
    "ADVERSARIAL_SCENARIO",
    "MUTATION_TEST",
    "EXECUTION_TRACE",
    "TEST_RESULT",
    "RUNTIME_OBSERVATION",
    "REPOSITORY_SNAPSHOT",
    "MODEL_DECISION",
    "CERTIFICATE_BINDING",
]

VerificationModality = Literal[
    "STATIC_ANALYSIS",
    "DIFFERENTIAL_EXECUTION",
    "HISTORICAL_GHOST_REPLAY",
    "METAMORPHIC_CHECK",
    "ADVERSARIAL_SCENARIO",
    "MUTATION_TEST",
]

RunStatus = Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED", "BLOCKED"]


class VersionedModel(BaseModel):
    """Base for every master contract: stable identity + semver version."""

    model_config = ConfigDict(extra="forbid")

    id: str
    version: str

    @field_validator("version")
    @classmethod
    def _validate_semver(cls, value: str) -> str:
        if not versioning.validate_version(value):
            raise ValueError(f"invalid semantic version: {value!r}")
        return value

    def immutable_key(self) -> str:
        """New-identity key binding this instance to its exact version."""
        return versioning.immutable_key(self.id, self.version)


class Task(VersionedModel):
    """A unit of governed work (Change Definition, §7.1)."""

    title: str
    change_id: str
    repository: str
    objective: str
    status: Literal[
        "CREATED",
        "INSPECTED",
        "PLANNED",
        "EXECUTING",
        "OBSERVED",
        "FAILED",
        "ITERATING",
        "VERIFYING",
        "VERIFIED",
        "BLOCKED",
    ]
    acceptance_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    created_at: datetime


class Action(VersionedModel):
    """A model decision recorded as an attributable action (AGENTS.md §12)."""

    agent_run_id: str
    action_type: Literal[
        "INSPECT",
        "PLAN",
        "MUTATE",
        "EXECUTE",
        "TEST",
        "VERIFY",
        "REPAIR",
        "CERTIFY",
        "DELEGATE",
        "DECIDE",
    ]
    rationale: str
    target: str
    expected_result: str
    performed_at: datetime


class ExecutionResult(VersionedModel):
    """A machine result; executions are authoritative over assertions."""

    tool_invocation_id: str
    command: str
    working_directory: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    started_at: datetime
    finished_at: datetime
    environment: dict[str, Any] = Field(default_factory=dict)


class ToolInvocation(VersionedModel):
    """An agent tool call referencing its originating action."""

    action_id: str
    invocation_id: str
    tool_name: str
    tool_type: Literal[
        "REPOSITORY",
        "FILE",
        "COMMAND",
        "TEST",
        "SANDBOX",
        "MODEL",
        "VERIFICATION",
        "CERTIFICATE",
    ]
    arguments: dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime
    execution_result: ExecutionResult | None = None


class Failure(VersionedModel):
    """A classified failure; failure is information (AGENTS.md §14)."""

    failure_id: str
    classification: FailureClassification
    summary: str
    observed_at: datetime
    evidence: str = ""
    probable_cause: str = ""
    next_action: str = ""
    related_execution: str = ""
    related_change_id: str = ""


class Evidence(VersionedModel):
    """A single evidence object bound to a claim (§2.2 evidence identity)."""

    claim_id: str
    evidence_type: EvidenceType
    source: str
    timestamp: datetime
    provenance: str = ""
    related_task_id: str = ""
    related_run_id: str = ""
    related_artifact: str = ""
    machine_result: dict[str, Any] = Field(default_factory=dict)
    hash: str = ""


class Claim(VersionedModel):
    """A protected/constitutional claim (e.g. AUTH-017)."""

    claim_id: str
    statement: str
    authority: str
    confidence: float = Field(ge=0, le=1)
    status: Literal[
        "OBSERVED",
        "PROTECTED",
        "UNVERIFIED",
        "LOCKED",
        "VIOLATED",
        "REPAIR_REQUIRED",
        "CERTIFIED",
        "HISTORICAL",
    ]
    locked: bool
    created_at: datetime
    evidence_ids: list[str] = Field(default_factory=list)


class BehavioralObject(VersionedModel):
    """A discovered/observed behavioral object (behavior, invariant, ghost...)."""

    object_type: Literal["BEHAVIOR", "INVARIANT", "INCIDENT", "DEPENDENCY", "RISK_ZONE", "GHOST"]
    name: str
    status: Literal["OBSERVED", "ACTIVE", "RESOLVED", "MONITORED", "PROTECTED"]
    description: str = ""
    claim_ids: list[str] = Field(default_factory=list)
    repository: str = ""
    created_at: datetime


class Intent(VersionedModel):
    """An intent ledger item (ADD/REPLACE/PRESERVE/PERFORMANCE/SECURITY)."""

    intent_type: Literal["ADD", "REPLACE", "PRESERVE", "PERFORMANCE", "SECURITY"]
    description: str
    change_id: str
    status: Literal["PROPOSED", "CONFIRMED", "LOCKED", "SUPERSEDED"]
    locked: bool
    created_at: datetime


class VerificationPlan(VersionedModel):
    """An immutable verification contract over claims (Phase 7 pre-coding lock)."""

    title: str
    claim_ids: list[str] = Field(min_length=1)
    modalities: list[VerificationModality] = Field(default_factory=list)
    status: Literal["DRAFT", "LOCKED", "COMPLETED", "SUPERSEDED"]
    locked: bool
    created_at: datetime


class CandidatePatch(VersionedModel):
    """A coding-agent delivery; candidate is never equivalent to certified."""

    change_id: str
    candidate_number: int = Field(ge=1)
    sandbox_id: str
    commit: str
    status: Literal["CANDIDATE", "REPAIRING", "VERIFIED", "REJECTED", "CERTIFIED"]
    description: str = ""
    verification_plan_id: str
    files: list[str] = Field(default_factory=list)
    applied_at: datetime


class BehavioralDelta(VersionedModel):
    """Observed difference introduced by a candidate (§10.1, AGENTS.md §18)."""

    change_id: str
    candidate_patch_id: str
    classification: Literal["ADDED", "REMOVED", "ALTERED", "UNCHANGED", "UNEXPLAINED"]
    claim_id: str
    authorized: bool | None = None
    intent_alignment: Literal["PENDING", "ALIGNED", "MISALIGNED"]
    observed_at: datetime
    evidence_ids: list[str] = Field(default_factory=list)


class RepairPackage(VersionedModel):
    """Structured, evidence-driven repair input (§10.4)."""

    failure_id: str
    expected_behavior: str
    observed_behavior: str
    affected_claim_id: str
    evidence_ids: list[str] = Field(min_length=1)
    suspected_path: str = ""
    required_outcome: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    created_at: datetime


class Certificate(VersionedModel):
    """Evidence-bound certification (AGENTS.md §19, plan §11.5)."""

    certificate_id: str
    change_id: str
    commit: str
    behavioral_delta_id: str
    verification_evidence_ids: list[str] = Field(min_length=1)
    intent_ledger_id: str = ""
    protected_behaviors: list[str] = Field(default_factory=list)
    candidate_patch_id: str
    environment: dict[str, Any] = Field(default_factory=dict)
    dependency_state: dict[str, Any] = Field(default_factory=dict)
    status: Literal["DRAFT", "ISSUED", "CERTIFIED", "REVOKED"]
    certificate_hash: str = ""
    evidence_traversal: list[str] = Field(default_factory=list)
    issued_at: datetime


class AgentRun(VersionedModel):
    """A lifecycle record of one agent run (orchestrator or specialist)."""

    role: Literal[
        "ORCHESTRATOR",
        "CODING",
        "VERIFICATION",
        "ARCHAEOLOGY",
        "EVIDENCE",
        "REPAIR",
        "CERTIFICATION",
        "INTENT",
        "IMPACT",
        "KNOWLEDGE",
    ]
    assignment_id: str
    status: RunStatus
    phase: str = ""
    summary: str = ""
    started_at: datetime
    finished_at: datetime | None = None


class SubagentRun(VersionedModel):
    """A parallel specialist run attributed to its parent agent run."""

    agent_run_id: str
    capability: Literal[
        "ARCHAEOLOGY",
        "KNOWLEDGE",
        "INTENT",
        "IMPACT",
        "CODING",
        "VERIFICATION",
        "EVIDENCE",
        "REPAIR",
        "CERTIFICATION",
    ]
    assignment_id: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    result_summary: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class PhaseGate(VersionedModel):
    """A machine-executable phase gate result (ADR-0007)."""

    phase: str
    status: Literal["PASS", "BLOCKED"]
    checks: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class ConsequentialEvent(BaseModel):
    """Structured §2.4 event; every consequential event becomes one of these.

    Not a master contract: events have no version and are append-only facts.
    """

    model_config = ConfigDict(extra="forbid")

    event_type: Literal[
        "TASK_RECEIVED",
        "REPOSITORY_INSPECTED",
        "PLAN_GENERATED",
        "SANDBOX_CREATED",
        "ACTION_EXECUTED",
        "RESULT_OBSERVED",
        "FAILURE_CLASSIFIED",
        "PATCH_GENERATED",
        "EVIDENCE_RECORDED",
        "VERIFICATION_RUN",
        "BEHAVIORAL_DELTA",
        "INTENT_ALIGNMENT",
        "REPAIR",
        "REVERIFICATION",
        "CERTIFICATION",
        "MEMORY_UPDATE",
        "MERGE",
        "BLOCKED",
    ]
    occurred_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T[0-9:.]{5,}(Z|[+-]\d{2}:\d{2})$")
    trace_id: str
    payload: dict[str, Any]
    related_task_id: str | None = None
    related_run_id: str | None = None
    related_claim_id: str | None = None
    related_certificate_id: str | None = None

    def occurred_at_dt(self) -> datetime:
        """Parse the ISO-8601 ``occurred_at`` string as a UTC datetime."""
        parsed = datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("occurred_at must carry a UTC offset")
        return parsed.astimezone(UTC)


CONTRACT_MODELS: dict[str, type[VersionedModel]] = {
    "task": Task,
    "action": Action,
    "tool_invocation": ToolInvocation,
    "execution_result": ExecutionResult,
    "failure": Failure,
    "evidence": Evidence,
    "claim": Claim,
    "behavioral_object": BehavioralObject,
    "intent": Intent,
    "verification_plan": VerificationPlan,
    "candidate_patch": CandidatePatch,
    "behavioral_delta": BehavioralDelta,
    "repair_package": RepairPackage,
    "certificate": Certificate,
    "agent_run": AgentRun,
    "subagent_run": SubagentRun,
    "phase_gate": PhaseGate,
}

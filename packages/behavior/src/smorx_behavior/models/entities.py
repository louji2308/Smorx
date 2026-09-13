"""Core behavioral entities (implementation plan phase 2, steps 2.1-2.4).

Thirty core entities plus the A2.4 consequential-event trace model. Every
model is a dialect-agnostic declarative mapping over
``smorx_behavior.db.base.Base`` and imports only the fixed persistence
contract: ``Base``, the UUID primary-key and timestamp mixins, and the
UTC-aware date-time type.

Ownership model (2.3): each governed concept exposes an explicit
``owner_scope`` marker and a foreign key to the object that owns the
semantic truth. Evidence identity (2.2) is a stable UUID primary key with a
unique SHA-256 hex digest. ``ConsequentialEvent`` is the 2.4 event/trace
model referencing any entity polymorphically via ``entity_type`` +
``entity_id``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smorx_behavior.db.base import Base
from smorx_behavior.db.mixins import TimestampMixin
from smorx_behavior.db.types import UTCDateTime

try:  # pragma: no cover - contract name; falls back to current db module name
    from smorx_behavior.db.mixins import UUIDPrimaryKeyMixin
except ImportError:  # pragma: no cover
    from smorx_behavior.db.mixins import UUIDPkMixin as UUIDPrimaryKeyMixin

from smorx_behavior.models.enums import (
    AgentState,
    CertificateStatus,
    ClaimStatus,
    ConstitutionStatus,
    DeltaDirection,
    EventKind,
    EvidenceType,
    FailureKind,
    IntentAlignmentStatus,
    IntentKind,
    IntentStatus,
    MemoryKind,
    Priority,
    RepairStatus,
    RunStatus,
    Severity,
    TaskStatus,
    VerificationStatus,
)

__all__ = [
    "AgentRun",
    "Behavior",
    "BehavioralDelta",
    "CandidatePatch",
    "Certificate",
    "Change",
    "Claim",
    "ConsequentialEvent",
    "Constitution",
    "ConstitutionClaim",
    "Dependency",
    "Evidence",
    "Execution",
    "Failure",
    "Ghost",
    "ImmutableObjectMixin",
    "Incident",
    "IntentAlignment",
    "IntentItem",
    "IntentLedger",
    "Invariant",
    "MemoryUpdate",
    "Project",
    "RepairPackage",
    "Repository",
    "RiskZone",
    "Run",
    "SemanticImpact",
    "SubagentRun",
    "Task",
    "VerificationCase",
    "VerificationPlan",
]


class ImmutableObjectMixin:
    """Version/lock columns for immutable-reference objects (2.5).

    Provided so versioned tables share one portable column shape. The
    ``locked`` flag marks an immutable reference; raising ``version`` under a
    lock creates a new identity rather than mutating history. Full versioning
    policy lives in the contracts layer.
    """

    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )
    locked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Root aggregate for a governed software-evolution project."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    repositories: Mapped[list[Repository]] = relationship(back_populates="project")
    tasks: Mapped[list[Task]] = relationship(back_populates="project")
    constitutions: Mapped[list[Constitution]] = relationship(back_populates="project")
    intent_ledgers: Mapped[list[IntentLedger]] = relationship(back_populates="project")
    certificates: Mapped[list[Certificate]] = relationship(back_populates="project")
    memory_updates: Mapped[list[MemoryUpdate]] = relationship(back_populates="project")


class Repository(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A version-controlled repository the system inspects and evolves."""

    __tablename__ = "repositories"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    default_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    vcs: Mapped[str] = mapped_column(String(50), default="git", nullable=False)
    last_inspected_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    project: Mapped[Project] = relationship(back_populates="repositories")
    changes: Mapped[list[Change]] = relationship(back_populates="repository")
    tasks: Mapped[list[Task]] = relationship(back_populates="repository")
    behaviors: Mapped[list[Behavior]] = relationship(back_populates="repository")
    incidents: Mapped[list[Incident]] = relationship(back_populates="repository")
    dependencies: Mapped[list[Dependency]] = relationship(back_populates="repository")
    risk_zones: Mapped[list[RiskZone]] = relationship(back_populates="repository")
    ghosts: Mapped[list[Ghost]] = relationship(back_populates="repository")


class Change(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A concrete proposed or committed change to a repository."""

    __tablename__ = "changes"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(100))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    author: Mapped[str | None] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="OPEN", nullable=False)
    changed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="changes")
    tasks: Mapped[list[Task]] = relationship(back_populates="change")
    executions: Mapped[list[Execution]] = relationship(back_populates="change")
    candidate_patches: Mapped[list[CandidatePatch]] = relationship(back_populates="change")
    verification_plans: Mapped[list[VerificationPlan]] = relationship(back_populates="change")
    behavioral_deltas: Mapped[list[BehavioralDelta]] = relationship(back_populates="change")
    intent_alignments: Mapped[list[IntentAlignment]] = relationship(back_populates="change")


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A unit of engineering work issued against a repository."""

    __tablename__ = "tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    repository_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("repositories.id"))
    change_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("changes.id"))
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(40), default=TaskStatus.CREATED.value, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(20), default=Priority.NORMAL.value, nullable=False
    )
    requested_by: Mapped[str | None] = mapped_column(String(120))
    acceptance_criteria: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    project: Mapped[Project] = relationship(back_populates="tasks")
    repository: Mapped[Repository | None] = relationship(back_populates="tasks")
    change: Mapped[Change | None] = relationship(back_populates="tasks")
    runs: Mapped[list[Run]] = relationship(back_populates="task")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="task")
    claims: Mapped[list[Claim]] = relationship(back_populates="task")
    failures: Mapped[list[Failure]] = relationship(back_populates="task")
    intent_items: Mapped[list[IntentItem]] = relationship(back_populates="task")
    semantic_impacts: Mapped[list[SemanticImpact]] = relationship(back_populates="task")
    verification_plans: Mapped[list[VerificationPlan]] = relationship(back_populates="task")
    candidate_patches: Mapped[list[CandidatePatch]] = relationship(back_populates="task")
    repair_packages: Mapped[list[RepairPackage]] = relationship(back_populates="task")
    behavioral_deltas: Mapped[list[BehavioralDelta]] = relationship(back_populates="task")
    intent_alignments: Mapped[list[IntentAlignment]] = relationship(back_populates="task")
    certificates: Mapped[list[Certificate]] = relationship(back_populates="task")
    memory_updates: Mapped[list[MemoryUpdate]] = relationship(back_populates="task")
    consequential_events: Mapped[list[ConsequentialEvent]] = relationship(back_populates="task")


class Run(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single execution attempt for a task."""

    __tablename__ = "runs"

    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tasks.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), default="AGENT", nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), default=RunStatus.QUEUED.value, nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    environment: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    task: Mapped[Task] = relationship(back_populates="runs")
    agent_runs: Mapped[list[AgentRun]] = relationship(back_populates="run")
    executions: Mapped[list[Execution]] = relationship(back_populates="run")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="run")
    failures: Mapped[list[Failure]] = relationship(back_populates="run")
    consequential_events: Mapped[list[ConsequentialEvent]] = relationship(back_populates="run")


class AgentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The reasoning loop of an orchestrator or specialist agent."""

    __tablename__ = "agent_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("runs.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(60), default="ORCHESTRATOR", nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    provider: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(
        String(40), default=RunStatus.QUEUED.value, nullable=False
    )
    state: Mapped[str] = mapped_column(
        String(40), default=AgentState.CREATED.value, nullable=False
    )
    iterations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_iterations: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    plan: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped[Run] = relationship(back_populates="agent_runs")
    subagent_runs: Mapped[list[SubagentRun]] = relationship(back_populates="agent_run")
    executions: Mapped[list[Execution]] = relationship(back_populates="agent_run")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="agent_run")
    candidate_patches: Mapped[list[CandidatePatch]] = relationship(back_populates="agent_run")


class SubagentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A bounded, contract-driven delegation performed by a specialist."""

    __tablename__ = "subagent_runs"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_runs.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    responsibility: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(40), default=RunStatus.QUEUED.value, nullable=False
    )
    inputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    evidence_ref: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    agent_run: Mapped[AgentRun] = relationship(back_populates="subagent_runs")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="subagent_run")


class Behavior(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An observed, nameable behavior of the repository."""

    __tablename__ = "behaviors"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False
    )
    origin_change_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("changes.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(60))
    protected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text)
    discovered_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="behaviors")
    origin_change: Mapped[Change | None] = relationship()
    invariants: Mapped[list[Invariant]] = relationship(back_populates="behavior")
    ghosts: Mapped[list[Ghost]] = relationship(back_populates="behavior")
    behavioral_deltas: Mapped[list[BehavioralDelta]] = relationship(back_populates="behavior")


class Invariant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A property that must remain true across the repository's evolution."""

    __tablename__ = "invariants"

    behavior_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("behaviors.id"))
    constitution_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("constitution_claims.id")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), default=Severity.MEDIUM.value, nullable=False
    )
    enforced_by: Mapped[str | None] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    behavior: Mapped[Behavior | None] = relationship(back_populates="invariants")
    constitution_claim: Mapped[ConstitutionClaim | None] = relationship(
        back_populates="invariants"
    )


class Incident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A real historical failure or degradation of repository behavior."""

    __tablename__ = "incidents"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False
    )
    change_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("changes.id"))
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence.id"))
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(
        String(20), default=Severity.MEDIUM.value, nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), default="OPEN", nullable=False)
    detected_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    repository: Mapped[Repository] = relationship(back_populates="incidents")
    change: Mapped[Change | None] = relationship()
    evidence: Mapped[Evidence | None] = relationship()


class Dependency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A package or service the repository depends on."""

    __tablename__ = "dependencies"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), default="PACKAGE", nullable=False)
    version_spec: Mapped[str | None] = mapped_column(String(120))
    ecosystem: Mapped[str | None] = mapped_column(String(60))
    source: Mapped[str | None] = mapped_column(String(200))
    risk_level: Mapped[str] = mapped_column(
        String(20), default=Severity.LOW.value, nullable=False
    )
    is_transitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="dependencies")


class RiskZone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A region of the repository with elevated change risk."""

    __tablename__ = "risk_zones"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False
    )
    path_pattern: Mapped[str] = mapped_column(String(400), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(
        String(20), default=Severity.MEDIUM.value, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="risk_zones")


class Ghost(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A hypothetical replay of a historical change against current behavior."""

    __tablename__ = "ghosts"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False
    )
    behavior_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("behaviors.id"))
    source_change_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("changes.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    hypothetical: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="CANDIDATE", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="ghosts")
    behavior: Mapped[Behavior | None] = relationship(back_populates="ghosts")
    source_change: Mapped[Change | None] = relationship()


class Evidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single, attributable observation supporting a claim (2.2).

    ``id`` is the stable identity, ``hash`` the unique SHA-256 hex digest of
    the underlying artifact/payload, and ``provenance`` the chain that
    produced it.
    """

    __tablename__ = "evidence"

    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("runs.id"))
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("agent_runs.id"))
    subagent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("subagent_runs.id")
    )
    execution_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("executions.id"))
    claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claims.id"))
    verification_case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("verification_cases.id")
    )
    type: Mapped[str] = mapped_column(
        String(60), default=EvidenceType.RUNTIME_OBSERVATION.value, nullable=False
    )
    occurred_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    source: Mapped[str | None] = mapped_column(String(200))
    provenance: Mapped[str | None] = mapped_column(Text)
    artifact: Mapped[str | None] = mapped_column(String(500))
    machine_result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    task: Mapped[Task | None] = relationship(back_populates="evidence_items")
    run: Mapped[Run | None] = relationship(back_populates="evidence_items")
    agent_run: Mapped[AgentRun | None] = relationship(back_populates="evidence_items")
    subagent_run: Mapped[SubagentRun | None] = relationship(back_populates="evidence_items")
    execution: Mapped[Execution | None] = relationship(back_populates="evidence_items")
    claim: Mapped[Claim | None] = relationship(back_populates="evidence_items")
    verification_case: Mapped[VerificationCase | None] = relationship(
        back_populates="evidence_items"
    )


class Claim(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An evidence-bound assertion about the system's behavior."""

    __tablename__ = "claims"

    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(60), default="BEHAVIORAL", nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), default=ClaimStatus.OPEN.value, nullable=False
    )
    confidence: Mapped[float | None] = mapped_column(Float)
    owner_type: Mapped[str] = mapped_column(String(60), default="CERTIFICATE", nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    task: Mapped[Task | None] = relationship(back_populates="claims")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="claim")
    behavioral_deltas: Mapped[list[BehavioralDelta]] = relationship(back_populates="claim")
    certificates: Mapped[list[Certificate]] = relationship(back_populates="claim")
    intent_alignments: Mapped[list[IntentAlignment]] = relationship(back_populates="claim")


class Constitution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The behavioral constitution: the governance source of truth (2.3)."""

    __tablename__ = "constitutions"

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    statement: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(40), default=ConstitutionStatus.DRAFT.value, nullable=False
    )
    owner_scope: Mapped[str] = mapped_column(
        String(60), default="GOVERNANCE", nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ratified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    project: Mapped[Project] = relationship(back_populates="constitutions")
    constitution_claims: Mapped[list[ConstitutionClaim]] = relationship(
        back_populates="constitution"
    )


class ConstitutionClaim(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single governance rule owned by a constitution."""

    __tablename__ = "constitution_claims"

    constitution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("constitutions.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(60), default="GOVERNANCE", nullable=False)
    rule: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), default=Severity.MEDIUM.value, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    constitution: Mapped[Constitution] = relationship(back_populates="constitution_claims")
    invariants: Mapped[list[Invariant]] = relationship(back_populates="constitution_claim")


class IntentLedger(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The user-intent source of truth for a task or project (2.3)."""

    __tablename__ = "intent_ledgers"

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str] = mapped_column(String(120), default="HUMAN", nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), default=IntentStatus.DRAFT.value, nullable=False
    )
    owner_scope: Mapped[str] = mapped_column(
        String(60), default="USER_INTENT", nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    project: Mapped[Project] = relationship(back_populates="intent_ledgers")
    task: Mapped[Task | None] = relationship()
    intent_items: Mapped[list[IntentItem]] = relationship(back_populates="intent_ledger")


class IntentItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single authorized requirement or constraint owned by a ledger."""

    __tablename__ = "intent_items"

    intent_ledger_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("intent_ledgers.id"), nullable=False
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(
        String(60), default=IntentKind.REQUIREMENT.value, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(20), default=Priority.NORMAL.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(40), default=IntentStatus.PENDING.value, nullable=False
    )
    authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(300))

    intent_ledger: Mapped[IntentLedger] = relationship(back_populates="intent_items")
    task: Mapped[Task | None] = relationship(back_populates="intent_items")
    intent_alignments: Mapped[list[IntentAlignment]] = relationship(
        back_populates="intent_item"
    )


class SemanticImpact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The semantic-impact map owning predicted impact (2.3)."""

    __tablename__ = "semantic_impacts"

    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tasks.id"), nullable=False)
    change_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("changes.id"))
    intent_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("intent_items.id"))
    description: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    impacted_behaviors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    impacted_artifacts: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False)
    owner_scope: Mapped[str] = mapped_column(String(60), default="IMPACT", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    task: Mapped[Task] = relationship(back_populates="semantic_impacts")
    change: Mapped[Change | None] = relationship()
    intent_item: Mapped[IntentItem | None] = relationship()


class VerificationPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The verification contract owning the independent investigation (2.3)."""

    __tablename__ = "verification_plans"

    change_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("changes.id"), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    intent_ledger_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("intent_ledgers.id")
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    strategy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    verification_contract: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False)
    owner_scope: Mapped[str] = mapped_column(
        String(60), default="VERIFICATION_CONTRACT", nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    change: Mapped[Change] = relationship(back_populates="verification_plans")
    task: Mapped[Task | None] = relationship(back_populates="verification_plans")
    intent_ledger: Mapped[IntentLedger | None] = relationship()
    verification_cases: Mapped[list[VerificationCase]] = relationship(
        back_populates="verification_plan"
    )
    certificates: Mapped[list[Certificate]] = relationship(back_populates="verification_plan")


class VerificationCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An independent verification experiment inside a verification plan."""

    __tablename__ = "verification_cases"

    verification_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("verification_plans.id"), nullable=False
    )
    change_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("changes.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(60), default=EvidenceType.STATIC_ANALYSIS.value, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(Text)
    expected: Mapped[str | None] = mapped_column(Text)
    threshold: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        String(40), default=VerificationStatus.PENDING.value, nullable=False
    )
    independent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owning_module: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    verification_plan: Mapped[VerificationPlan] = relationship(
        back_populates="verification_cases"
    )
    change: Mapped[Change | None] = relationship()
    executions: Mapped[list[Execution]] = relationship(back_populates="verification_case")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="verification_case")


class CandidatePatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A candidate development output produced by the coding agent (2.3)."""

    __tablename__ = "candidate_patches"

    change_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("changes.id"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tasks.id"), nullable=False)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("agent_runs.id"))
    base_commit: Mapped[str | None] = mapped_column(String(64))
    patch_ref: Mapped[str | None] = mapped_column(String(500))
    diff: Mapped[str | None] = mapped_column(Text)
    files_changed: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="PROPOSED", nullable=False)
    candidate_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    proposed_by: Mapped[str | None] = mapped_column(String(120))
    owner_scope: Mapped[str] = mapped_column(
        String(60), default="DEVELOPMENT_OUTPUT", nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    change: Mapped[Change] = relationship(back_populates="candidate_patches")
    task: Mapped[Task] = relationship(back_populates="candidate_patches")
    agent_run: Mapped[AgentRun | None] = relationship(back_populates="candidate_patches")
    executions: Mapped[list[Execution]] = relationship(back_populates="candidate_patch")
    failures: Mapped[list[Failure]] = relationship(back_populates="candidate_patch")
    repair_packages: Mapped[list[RepairPackage]] = relationship(back_populates="candidate_patch")


class Execution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A machine-authoritative sandbox execution and its raw result."""

    __tablename__ = "executions"

    run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("runs.id"), nullable=False)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("agent_runs.id"))
    change_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("changes.id"))
    candidate_patch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("candidate_patches.id")
    )
    verification_case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("verification_cases.id")
    )
    sandbox_id: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(60), default="COMMAND", nullable=False)
    command: Mapped[str | None] = mapped_column(Text)
    cwd: Mapped[str | None] = mapped_column(String(500))
    exit_code: Mapped[int | None] = mapped_column(Integer)
    stdout: Mapped[str | None] = mapped_column(Text)
    stderr: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(40), default=VerificationStatus.PENDING.value, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    environment: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    machine_result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped[Run] = relationship(back_populates="executions")
    agent_run: Mapped[AgentRun | None] = relationship(back_populates="executions")
    change: Mapped[Change | None] = relationship(back_populates="executions")
    candidate_patch: Mapped[CandidatePatch | None] = relationship(
        back_populates="executions"
    )
    verification_case: Mapped[VerificationCase | None] = relationship(
        back_populates="executions"
    )
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="execution")
    failures: Mapped[list[Failure]] = relationship(back_populates="execution")


class Failure(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A classified, preserved failure that drives the next decision (I4)."""

    __tablename__ = "failures"

    execution_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("executions.id"))
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("runs.id"))
    candidate_patch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("candidate_patches.id")
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence.id"))
    classification: Mapped[str] = mapped_column(
        String(60), default=FailureKind.F7_TOOL.value, nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    probable_cause: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(
        String(20), default=Severity.MEDIUM.value, nullable=False
    )
    iteration: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    execution: Mapped[Execution | None] = relationship(back_populates="failures")
    task: Mapped[Task | None] = relationship(back_populates="failures")
    run: Mapped[Run | None] = relationship(back_populates="failures")
    candidate_patch: Mapped[CandidatePatch | None] = relationship(
        back_populates="failures"
    )
    evidence: Mapped[Evidence | None] = relationship()
    repair_packages: Mapped[list[RepairPackage]] = relationship(back_populates="failure")


class BehavioralDelta(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The observed behavioral difference owning what actually changed (2.3)."""

    __tablename__ = "behavioral_deltas"

    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    change_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("changes.id"))
    claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claims.id"))
    behavior_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("behaviors.id"))
    execution_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("executions.id"))
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence.id"))
    certificate_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("certificates.id"))
    metric: Mapped[str | None] = mapped_column(String(200))
    baseline_value: Mapped[str | None] = mapped_column(String(200))
    candidate_value: Mapped[str | None] = mapped_column(String(200))
    magnitude: Mapped[float | None] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(
        String(20), default=DeltaDirection.UNCHANGED.value, nullable=False
    )
    category: Mapped[str] = mapped_column(String(60), default="BEHAVIORAL", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    observed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_scope: Mapped[str] = mapped_column(
        String(60), default="OBSERVED_DIFFERENCE", nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    task: Mapped[Task | None] = relationship(back_populates="behavioral_deltas")
    change: Mapped[Change | None] = relationship(back_populates="behavioral_deltas")
    claim: Mapped[Claim | None] = relationship(back_populates="behavioral_deltas")
    behavior: Mapped[Behavior | None] = relationship(back_populates="behavioral_deltas")
    execution: Mapped[Execution | None] = relationship()
    evidence: Mapped[Evidence | None] = relationship()
    certificate: Mapped[Certificate | None] = relationship(
        back_populates="behavioral_deltas",
        foreign_keys="[BehavioralDelta.certificate_id]",
    )


class IntentAlignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Authorization verdict: was the observed change permitted? (section 18)."""

    __tablename__ = "intent_alignments"

    intent_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("intent_items.id"), nullable=False
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claims.id"))
    change_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("changes.id"))
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence.id"))
    status: Mapped[str] = mapped_column(
        String(40), default=IntentAlignmentStatus.PENDING.value, nullable=False
    )
    verdict: Mapped[str | None] = mapped_column(String(40))
    rationale: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    verified_by: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    intent_item: Mapped[IntentItem] = relationship(back_populates="intent_alignments")
    task: Mapped[Task | None] = relationship(back_populates="intent_alignments")
    claim: Mapped[Claim | None] = relationship(back_populates="intent_alignments")
    change: Mapped[Change | None] = relationship(back_populates="intent_alignments")
    evidence: Mapped[Evidence | None] = relationship()
    certificates: Mapped[list[Certificate]] = relationship(
        back_populates="intent_alignment"
    )


class RepairPackage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A bounded repair attempt generated in response to a failure."""

    __tablename__ = "repair_packages"

    failure_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("failures.id"))
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    candidate_patch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("candidate_patches.id")
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence.id"))
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    patch_ref: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(40), default=RepairStatus.CREATED.value, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    failure: Mapped[Failure | None] = relationship(back_populates="repair_packages")
    task: Mapped[Task | None] = relationship(back_populates="repair_packages")
    candidate_patch: Mapped[CandidatePatch | None] = relationship(
        back_populates="repair_packages"
    )
    evidence: Mapped[Evidence | None] = relationship()


class Certificate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The certification owning proof bound to implementation and evidence (2.3)."""

    __tablename__ = "certificates"

    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("projects.id"))
    claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claims.id"))
    verification_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("verification_plans.id")
    )
    intent_alignment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("intent_alignments.id")
    )
    certificate_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(40), default=CertificateStatus.DRAFT.value, nullable=False
    )
    owner_scope: Mapped[str] = mapped_column(
        String(60), default="CERTIFICATION", nullable=False
    )
    signature: Mapped[str | None] = mapped_column(String(200))
    evidence_hash: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    task: Mapped[Task | None] = relationship(back_populates="certificates")
    project: Mapped[Project | None] = relationship(back_populates="certificates")
    claim: Mapped[Claim | None] = relationship(back_populates="certificates")
    behavioral_deltas: Mapped[list[BehavioralDelta]] = relationship(
        back_populates="certificate", foreign_keys="[BehavioralDelta.certificate_id]"
    )
    verification_plan: Mapped[VerificationPlan | None] = relationship(
        back_populates="certificates"
    )
    intent_alignment: Mapped[IntentAlignment | None] = relationship(
        back_populates="certificates"
    )
    memory_updates: Mapped[list[MemoryUpdate]] = relationship(back_populates="certificate")


class MemoryUpdate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A behavioral-memory entry closing the loop back into future tasks."""

    __tablename__ = "memory_updates"

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    certificate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("certificates.id")
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence.id"))
    kind: Mapped[str] = mapped_column(
        String(60), default=MemoryKind.BEHAVIORAL_MEMORY.value, nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(120))
    memory_ref: Mapped[str | None] = mapped_column(String(300))

    project: Mapped[Project] = relationship(back_populates="memory_updates")
    certificate: Mapped[Certificate | None] = relationship(back_populates="memory_updates")
    task: Mapped[Task | None] = relationship(back_populates="memory_updates")
    evidence: Mapped[Evidence | None] = relationship()


class ConsequentialEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A2.4 event and trace model.

    Every consequential event becomes a structured, attributable row. The
    affected entity is referenced polymorphically through ``entity_type`` +
    ``entity_id`` (no FK, so any entity may be traced without schema
    coupling); ``payload`` carries the structured detail and ``provenance``
    the reference into the evidence chain.
    """

    __tablename__ = "consequential_events"

    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(60), default=EventKind.ACTION_EXECUTED.value, nullable=False
    )
    occurred_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    actor: Mapped[str | None] = mapped_column(String(120))
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provenance: Mapped[str | None] = mapped_column(Text)
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("runs.id"))
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hash: Mapped[str | None] = mapped_column(String(64))

    task: Mapped[Task | None] = relationship(back_populates="consequential_events")
    run: Mapped[Run | None] = relationship(back_populates="consequential_events")

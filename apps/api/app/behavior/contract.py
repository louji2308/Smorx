"""Behavior API contracts for the Phase 6 backend adapter (Discover + Govern).

This module is the *interface artifact* for the Phase 6 behavior adapter. It
declares the exact wire shapes the web client consumes (camelCase, mirroring
``apps/web/src/types/index.ts`` and the Discover/Govern components) and the
``BehaviorAdapter`` protocol every implementation must satisfy. It contains no
persistence or query logic; the SQLAlchemy implementation lives in
``app.behavior.adapter`` and is injected into the FastAPI router so the two can
be developed and tested independently.

Honesty contract (AGENTS.md §3, §13, §39): every value an adapter returns must
be derived from persisted rows in the behavioral database (seeded by the
deterministic ``smorx_behavior.seed.demo`` fixture). No fabricated statuses, no
hardcoded demo counts, no simulated execution traces. Empty categories return
``count == 0`` with an empty item list; they are never padded to match a demo
narrative.

Ownership: this file is the ownership boundary between the data layer
(``app.behavior.*``) and the HTTP layer (``app.api.behavior_routes``).
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class ProjectDto(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None


class RepositoryDto(BaseModel):
    id: str
    name: str
    url: str | None = None
    default_branch: str = "main"
    last_inspected_at: str | None = None


class ChangeDto(BaseModel):
    id: str
    external_id: str | None = None
    title: str
    description: str | None = None
    status: str = "OPEN"
    commit_sha: str | None = None


class ConstitutionDto(BaseModel):
    id: str
    title: str
    version: int = 1
    status: str = "DRAFT"  # DRAFT | REVIEW | ACTIVE | LOCKED
    claim_count: int = 0
    protected_count: int = 0
    locked: bool = False


class BehaviorContext(BaseModel):
    """Root context for the shell: project, repository, change, governing context."""

    project: ProjectDto | None = None
    repository: RepositoryDto | None = None
    change: ChangeDto | None = None
    constitution: ConstitutionDto | None = None


class FindingItemDto(BaseModel):
    """One archaeology finding row (matches the Evidence Workspace item shape).

    ``type`` follows the behavioral object vocabulary: BEHAVIOR, INVARIANT,
    INCIDENT, DEPENDENCY, RISK_ZONE, GHOST.
    """

    id: str
    name: str
    type: str
    description: str | None = None
    status: str = "OBSERVED"
    confidence: float | None = None
    protected: bool | None = None
    evidence_count: int | None = None
    severity: str | None = None
    detected_at: str | None = None
    statement: str | None = None
    version: str | None = None
    risk: str | None = None
    ecosystem: str | None = None


class EvidenceDto(BaseModel):
    id: str
    claim_id: str | None = None
    evidence_type: str
    source: str | None = None
    timestamp: str | None = None
    provenance: str | None = None
    related_task_id: str | None = None
    related_run_id: str | None = None
    related_artifact: str | None = None
    machine_result: dict[str, Any] = {}
    hash: str


class FindingsCategory(BaseModel):
    count: int
    items: list[dict[str, Any]]


class FindingsSet(BaseModel):
    """Archaeology findings grouped by the Evidence Workspace categories."""

    behaviors: FindingsCategory
    invariants: FindingsCategory
    incidents: FindingsCategory
    dependencies: FindingsCategory
    couplings: FindingsCategory
    risk_zones: FindingsCategory
    ghosts: FindingsCategory
    evidence: FindingsCategory


class BehavioralObjectDto(BaseModel):
    id: str
    object_type: str  # BEHAVIOR | INVARIANT | INCIDENT | DEPENDENCY | RISK_ZONE | GHOST
    name: str
    description: str | None = None
    status: str = "ACTIVE"
    confidence: float | None = None
    protected: bool | None = None
    discovered_at: str | None = None
    repository_id: str
    claim_ids: list[str] = []
    metadata: dict[str, Any] = {}


class GraphNodeDto(BaseModel):
    id: str
    type: str  # BehavioralObjectType
    position: dict[str, float]  # {"x": ..., "y": ...}
    label: str
    trust_state: str  # TrustState
    data: BehavioralObjectDto


class GraphEdgeDto(BaseModel):
    id: str
    source: str
    target: str
    type: str = "animated"
    label: str | None = None


class GraphDto(BaseModel):
    nodes: list[GraphNodeDto]
    edges: list[GraphEdgeDto]


class ClaimDto(BaseModel):
    """A governed claim (matches the Constitution Workspace ``ClaimData``)."""

    id: str
    claim_id: str
    statement: str
    authority: str
    confidence: float | None = None
    status: str = "OBSERVED"  # TrustState
    locked: bool = False
    created_at: str
    evidence_ids: list[str] = []
    affected_software: list[str] = []
    governance_consequence: str | None = None
    verification_requirements: list[str] = []


class ConstitutionVersionDto(BaseModel):
    id: str
    version: int = 1
    title: str
    status: str = "DRAFT"
    claim_count: int = 0
    protected_count: int = 0
    observed_count: int = 0
    hypothesis_count: int = 0
    conflict_count: int = 0
    ratified_at: str | None = None
    locked: bool = False


class ConstitutionView(BaseModel):
    version: ConstitutionVersionDto
    claims: list[ClaimDto]
    counts: dict[str, int]  # protected | observed | hypotheses | conflicts


class ReadinessStepDto(BaseModel):
    id: str
    label: str
    state: str  # TrustState
    met: bool


class ReadinessView(BaseModel):
    steps: list[ReadinessStepDto]
    met_count: int
    total: int
    ready: bool


class ActivateResult(BaseModel):
    """Outcome of the constitution activation attempt.

    ``status`` is one of:

    - ``ACTIVE`` — a constitution was moved to ACTIVE in this call;
    - ``ALREADY_ACTIVE`` — the constitution was already ACTIVE (idempotent);
    - ``NOT_DRAFTED`` — no persisted constitution exists to activate; nothing
      is fabricated and no row is created (honesty contract §3/§39).
    """

    status: str  # ACTIVE | ALREADY_ACTIVE | NOT_DRAFTED
    constitution: ConstitutionDto
    claim_count: int
    protected_count: int
    ratified_at: str | None = None
    message: str | None = None


class BehaviorAdapter(Protocol):
    """Every Phase 6 behavior adapter must satisfy this interface.

    Implementations own their database/session lifecycle; callers interact only
    through these methods. Results are always derived from persisted rows.
    """

    def context(self) -> BehaviorContext: ...

    def findings(self) -> FindingsSet: ...

    def graph(self) -> GraphDto: ...

    def constitution(self) -> ConstitutionView: ...

    def readiness(self) -> ReadinessView: ...

    def activate(self) -> ActivateResult: ...

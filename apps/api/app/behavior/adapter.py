# mypy: disable-error-code="import-untyped"

"""SQLAlchemy implementation of the Phase 6 ``BehaviorAdapter`` (Discover + Govern).

Read-only projection over the persisted ``smorx_behavior`` behavioral database
seeded by the deterministic ``smorx_behavior.seed.demo`` fixture. Every value
returned is derived from persisted rows (AGENTS.md sections 3/13/39): empty
categories are reported as ``count == 0`` with empty item lists, and
``activate()`` never fabricates a constitution when none exists.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from smorx_behavior.models import (
    Behavior,
    Change,
    Constitution,
    ConstitutionClaim,
    Dependency,
    Evidence,
    Ghost,
    Incident,
    Invariant,
    Project,
    Repository,
    RiskZone,
    Task,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.behavior.contract import (
    ActivateResult,
    BehaviorAdapter,
    BehavioralObjectDto,
    BehaviorContext,
    ChangeDto,
    ClaimDto,
    ConstitutionDto,
    ConstitutionVersionDto,
    ConstitutionView,
    FindingItemDto,
    FindingsCategory,
    FindingsSet,
    GraphDto,
    GraphEdgeDto,
    GraphNodeDto,
    ProjectDto,
    ReadinessStepDto,
    ReadinessView,
    RepositoryDto,
)
from app.behavior.database import (
    DEFAULT_BEHAVIOR_DATABASE_URL,
    behavior_session_factory,
    create_behavior_engine,
    ensure_behavior_schema,
    seed_demo_scenario_if_empty,
)

__all__ = ["SqlAlchemyBehaviorAdapter", "build_behavior_adapter"]


def _iso(value: datetime | None) -> str | None:
    """Render a datetime as ISO-8601 text, or ``None`` when absent."""
    return value.isoformat() if value is not None else None


class SqlAlchemyBehaviorAdapter(BehaviorAdapter):
    """Projection and governed activation over the behavioral database.

    Every method opens a fresh ``Session`` from the injected factory and
    closes it on return. Read-only methods never commit; ``activate()``
    commits the sole real transition.
    """

    def __init__(
        self, session_factory: Callable[[], Session], *, project_id: uuid.UUID | None = None
    ) -> None:
        self._session_factory = session_factory
        self._project_id = project_id

    # -- context -----------------------------------------------------------

    def context(self) -> BehaviorContext:
        with self._session_factory() as session:
            project = self._resolve_project(session)
            if project is None:
                return BehaviorContext()
            repository = self._resolve_repository(session, project)
            change = self._resolve_change(session, repository) if repository is not None else None
            protected_count = self._protected_behavior_count(session, project)
            return BehaviorContext(
                project=ProjectDto(
                    id=str(project.id),
                    name=project.name,
                    slug=project.slug,
                    description=project.description,
                ),
                repository=(
                    RepositoryDto(
                        id=str(repository.id),
                        name=repository.name,
                        url=repository.url,
                        default_branch=repository.default_branch,
                        last_inspected_at=_iso(repository.last_inspected_at),
                    )
                    if repository is not None
                    else None
                ),
                change=(
                    ChangeDto(
                        id=str(change.id),
                        external_id=change.external_id,
                        title=change.title,
                        description=change.description,
                        status=change.status,
                        commit_sha=change.commit_sha,
                    )
                    if change is not None
                    else None
                ),
                constitution=self._constitution_dto(
                    session, self._resolve_constitution(session, project), protected_count
                ),
            )

    # -- findings -----------------------------------------------------------

    def findings(self) -> FindingsSet:
        with self._session_factory() as session:
            project = self._resolve_project(session)
            if project is None:
                return self._empty_findings()
            repository = self._resolve_repository(session, project)
            if repository is None:
                return self._empty_findings()

            behaviors = self._category(
                FindingItemDto(
                    id=str(row.id),
                    name=row.name,
                    type="BEHAVIOR",
                    description=row.description,
                    status="OBSERVED",
                    protected=row.protected,
                    detected_at=_iso(row.discovered_at),
                )
                for row in self._repository_rows(session, Behavior, repository.id)
            )
            invariants = self._category(
                FindingItemDto(
                    id=str(row.id),
                    name=row.name,
                    type="INVARIANT",
                    severity=row.severity,
                    statement=row.statement,
                    version=str(row.version),
                )
                for row in self._project_invariants(session, project)
            )
            incidents = self._category(
                FindingItemDto(
                    id=str(row.id),
                    name=row.title,
                    type="INCIDENT",
                    description=row.description,
                    status=row.status,
                    severity=row.severity,
                    detected_at=_iso(row.detected_at),
                )
                for row in self._repository_rows(session, Incident, repository.id)
            )
            dependencies = self._category(
                FindingItemDto(
                    id=str(row.id),
                    name=row.name,
                    type="DEPENDENCY",
                    version=row.version_spec,
                    risk=row.risk_level,
                    ecosystem=row.ecosystem,
                )
                for row in self._repository_rows(session, Dependency, repository.id)
            )
            couplings = self._category([])
            risk_zones = self._category(
                FindingItemDto(
                    id=str(row.id),
                    name=row.path_pattern,
                    type="RISK_ZONE",
                    description=row.reason,
                    severity=row.severity,
                    risk=row.severity,
                )
                for row in self._repository_rows(session, RiskZone, repository.id)
            )
            ghosts = self._category(
                FindingItemDto(
                    id=str(row.id),
                    name=row.name,
                    type="GHOST",
                    description=row.description,
                    status=row.status,
                    version=str(row.version),
                )
                for row in self._repository_rows(session, Ghost, repository.id)
            )
            evidence = self._category(
                FindingItemDto(
                    id=str(row.id),
                    name=row.artifact or row.source or f"evidence:{row.hash[:8]}",
                    type=row.type,
                    description=row.provenance,
                    status="OBSERVED",
                    statement=row.artifact,
                    detected_at=_iso(row.occurred_at),
                )
                for row in self._project_evidence(session, project)
            )
            return FindingsSet(
                behaviors=behaviors,
                invariants=invariants,
                incidents=incidents,
                dependencies=dependencies,
                couplings=couplings,
                risk_zones=risk_zones,
                ghosts=ghosts,
                evidence=evidence,
            )

    # -- graph ----------------------------------------------------------------

    def graph(self) -> GraphDto:
        with self._session_factory() as session:
            project = self._resolve_project(session)
            if project is None:
                return GraphDto(nodes=[], edges=[])
            repository = self._resolve_repository(session, project)
            if repository is None:
                return GraphDto(nodes=[], edges=[])
            constitution = self._resolve_constitution(session, project)
            constitution_active = constitution is not None and constitution.status == "ACTIVE"

            behaviors = self._repository_rows(session, Behavior, repository.id)
            ghosts = self._repository_rows(session, Ghost, repository.id)
            incidents = self._repository_rows(session, Incident, repository.id)
            dependencies = self._repository_rows(session, Dependency, repository.id)
            risk_zones = self._repository_rows(session, RiskZone, repository.id)
            invariants = self._behavior_linked_invariants(session, repository.id)

            nodes: list[GraphNodeDto] = []
            node_ids: set[str] = set()

            def emit(
                index: int,
                *,
                node_id: str,
                object_type: str,
                name: str,
                description: str | None,
                status: str,
                protected: bool | None,
                discovered_at: datetime | None,
                repository_id: str,
                trust_state: str,
            ) -> None:
                nodes.append(
                    self._make_graph_node(
                        index,
                        node_id=node_id,
                        object_type=object_type,
                        name=name,
                        description=description,
                        status=status,
                        protected=protected,
                        discovered_at=discovered_at,
                        repository_id=repository_id,
                        trust_state=trust_state,
                    )
                )
                node_ids.add(node_id)

            index = 0
            for row in behaviors:
                emit(
                    index,
                    node_id=str(row.id),
                    object_type="BEHAVIOR",
                    name=row.name,
                    description=row.description,
                    status="ACTIVE",
                    protected=row.protected,
                    discovered_at=row.discovered_at,
                    repository_id=str(repository.id),
                    trust_state=self._trust_state(row.locked, row.protected, constitution_active),
                )
                index += 1
            for row in invariants:
                emit(
                    index,
                    node_id=str(row.id),
                    object_type="INVARIANT",
                    name=row.name,
                    description=row.statement,
                    status="ACTIVE",
                    protected=None,
                    discovered_at=None,
                    repository_id=str(repository.id),
                    trust_state=self._trust_state(row.locked, None, False),
                )
                index += 1
            for row in ghosts:
                emit(
                    index,
                    node_id=str(row.id),
                    object_type="GHOST",
                    name=row.name,
                    description=row.description,
                    status="OBSERVED",
                    protected=None,
                    discovered_at=None,
                    repository_id=str(repository.id),
                    trust_state="OBSERVED",
                )
                index += 1
            for row in incidents:
                emit(
                    index,
                    node_id=str(row.id),
                    object_type="INCIDENT",
                    name=row.title,
                    description=row.description,
                    status=row.status,
                    protected=None,
                    discovered_at=None,
                    repository_id=str(repository.id),
                    trust_state="OBSERVED",
                )
                index += 1
            for row in dependencies:
                emit(
                    index,
                    node_id=str(row.id),
                    object_type="DEPENDENCY",
                    name=row.name,
                    description=row.version_spec,
                    status="ACTIVE",
                    protected=None,
                    discovered_at=None,
                    repository_id=str(repository.id),
                    trust_state="OBSERVED",
                )
                index += 1
            for row in risk_zones:
                emit(
                    index,
                    node_id=str(row.id),
                    object_type="RISK_ZONE",
                    name=row.path_pattern,
                    description=row.reason,
                    status="ACTIVE",
                    protected=None,
                    discovered_at=None,
                    repository_id=str(repository.id),
                    trust_state="OBSERVED",
                )
                index += 1

            edges: list[GraphEdgeDto] = []
            for row in ghosts:
                if row.behavior_id is not None:
                    self._append_edge(edges, str(row.id), str(row.behavior_id), node_ids, "replay")
            for row in invariants:
                if row.behavior_id is not None:
                    self._append_edge(
                        edges, str(row.id), str(row.behavior_id), node_ids, "protects"
                    )
            return GraphDto(nodes=nodes, edges=edges)

    # -- constitution -----------------------------------------------------------

    def constitution(self) -> ConstitutionView:
        with self._session_factory() as session:
            project = self._resolve_project(session)
            protected_count = self._protected_behavior_count(session, project) if project else 0
            constitution = self._resolve_constitution(session, project) if project else None
            if constitution is None:
                return ConstitutionView(
                    version=ConstitutionVersionDto(
                        id="",
                        version=1,
                        title="",
                        status="DRAFT",
                        claim_count=0,
                        protected_count=protected_count,
                        observed_count=0,
                        hypothesis_count=0,
                        conflict_count=0,
                        locked=False,
                    ),
                    claims=[],
                    counts={
                        "protected": protected_count,
                        "observed": 0,
                        "hypotheses": 0,
                        "conflicts": 0,
                    },
                )

            claims = list(
                session.scalars(
                    select(ConstitutionClaim)
                    .where(ConstitutionClaim.constitution_id == constitution.id)
                    .order_by(ConstitutionClaim.position, ConstitutionClaim.id)
                )
            )
            claim_dtos = [
                ClaimDto(
                    id=str(row.id),
                    claim_id=str(row.id),
                    statement=row.rule,
                    authority=row.category,
                    status="LOCKED" if constitution.locked else "OBSERVED",
                    locked=row.locked,
                    created_at=row.created_at.isoformat(),
                    evidence_ids=[],
                    affected_software=[],
                    governance_consequence=None,
                    verification_requirements=[],
                )
                for row in claims
            ]
            observed_count = sum(1 for claim in claim_dtos if claim.status == "OBSERVED")
            counts = {
                "protected": protected_count,
                "observed": observed_count,
                "hypotheses": 0,
                "conflicts": 0,
            }
            return ConstitutionView(
                version=ConstitutionVersionDto(
                    id=str(constitution.id),
                    version=constitution.version,
                    title=constitution.title,
                    status=constitution.status,
                    claim_count=len(claims),
                    protected_count=protected_count,
                    observed_count=observed_count,
                    hypothesis_count=0,
                    conflict_count=0,
                    ratified_at=_iso(constitution.ratified_at),
                    locked=constitution.locked,
                ),
                claims=claim_dtos,
                counts=counts,
            )

    # -- readiness ---------------------------------------------------------------

    def readiness(self) -> ReadinessView:
        with self._session_factory() as session:
            project = self._resolve_project(session)
            repository = self._resolve_repository(session, project) if project else None
            constitution = self._resolve_constitution(session, project) if project else None

            behavior_count = self._behavior_count(session, repository.id) if repository else 0
            ghost_count = self._ghost_count(session, repository.id) if repository else 0
            evidence_count = self._evidence_count(session, project) if project else 0
            claim_count = (
                self._constitution_claim_count(session, constitution)
                if constitution is not None
                else 0
            )

            archaeology_met = behavior_count > 0 and ghost_count > 0
            evidence_met = evidence_count > 0
            constitution_met = constitution is not None and claim_count > 0
            ratified_met = constitution is not None and constitution.status == "ACTIVE"

            steps = [
                ReadinessStepDto(
                    id="archaeology",
                    label="Software archaeology complete",
                    state="OBSERVED" if archaeology_met else "UNVERIFIED",
                    met=archaeology_met,
                ),
                ReadinessStepDto(
                    id="evidence",
                    label="Evidence recorded",
                    state="OBSERVED" if evidence_met else "UNVERIFIED",
                    met=evidence_met,
                ),
                ReadinessStepDto(
                    id="constitution",
                    label="Constitution drafted",
                    state="OBSERVED" if constitution_met else "UNVERIFIED",
                    met=constitution_met,
                ),
                ReadinessStepDto(
                    id="ratified",
                    label="Constitution ratified",
                    state="OBSERVED" if ratified_met else "UNVERIFIED",
                    met=ratified_met,
                ),
            ]
            met_count = sum(1 for step in steps if step.met)
            return ReadinessView(steps=steps, met_count=met_count, total=4, ready=met_count == 4)

    # -- activate -------------------------------------------------------------------

    def activate(self) -> ActivateResult:
        with self._session_factory() as session:
            project = self._resolve_project(session)
            protected_count = self._protected_behavior_count(session, project) if project else 0
            constitution = self._resolve_constitution(session, project) if project else None
            if constitution is None:
                return ActivateResult(
                    status="NOT_DRAFTED",
                    constitution=ConstitutionDto(
                        id="", title="", status="DRAFT", claim_count=0
                    ),
                    claim_count=0,
                    protected_count=protected_count,
                    message="no persisted constitution exists to activate; nothing fabricated",
                )

            if constitution.status == "ACTIVE":
                claim_count = self._constitution_claim_count(session, constitution)
                return ActivateResult(
                    status="ALREADY_ACTIVE",
                    constitution=self._constitution_dto(session, constitution, protected_count),
                    claim_count=claim_count,
                    protected_count=protected_count,
                    ratified_at=_iso(constitution.ratified_at),
                )

            constitution.status = "ACTIVE"
            constitution.ratified_at = datetime.now(UTC)
            session.commit()
            claim_count = self._constitution_claim_count(session, constitution)
            return ActivateResult(
                status="ACTIVE",
                constitution=self._constitution_dto(session, constitution, protected_count),
                claim_count=claim_count,
                protected_count=protected_count,
                ratified_at=_iso(constitution.ratified_at),
            )

    # -- selection -------------------------------------------------------------------

    def _resolve_project(self, session: Session) -> Project | None:
        if self._project_id is not None:
            return session.get(Project, self._project_id)
        return session.scalars(select(Project).order_by(Project.id)).first()

    def _resolve_repository(self, session: Session, project: Project) -> Repository | None:
        return session.scalars(
            select(Repository)
            .where(Repository.project_id == project.id)
            .order_by(Repository.id)
        ).first()

    def _resolve_change(self, session: Session, repository: Repository) -> Change | None:
        return session.scalars(
            select(Change)
            .where(Change.repository_id == repository.id)
            .order_by(func.coalesce(Change.changed_at, Change.created_at).desc(), Change.id)
        ).first()

    def _resolve_constitution(self, session: Session, project: Project) -> Constitution | None:
        return session.scalars(
            select(Constitution)
            .where(Constitution.project_id == project.id)
            .order_by(Constitution.version.desc(), Constitution.updated_at.desc(), Constitution.id)
        ).first()

    # -- derived queries ----------------------------------------------------------------

    def _repository_rows(
        self, session: Session, model: type[Any], repository_id: uuid.UUID
    ) -> Sequence[Any]:
        return session.scalars(
            select(model).where(model.repository_id == repository_id).order_by(model.id)
        ).all()

    def _behavior_linked_invariants(
        self, session: Session, repository_id: uuid.UUID
    ) -> Sequence[Invariant]:
        return session.scalars(
            select(Invariant)
            .join(Invariant.behavior)
            .where(Behavior.repository_id == repository_id)
            .order_by(Invariant.id)
        ).all()

    def _project_invariants(self, session: Session, project: Project) -> list[Invariant]:
        behavior_linked = self._behavior_linked_invariants(
            session, self._repository_id_for_project(session, project)
        )
        claim_linked = list(
            session.scalars(
                select(Invariant)
                .join(Invariant.constitution_claim)
                .join(ConstitutionClaim.constitution)
                .where(Constitution.project_id == project.id)
                .order_by(Invariant.id)
            )
        )
        merged: dict[uuid.UUID, Invariant] = {}
        for row in (*behavior_linked, *claim_linked):
            merged[row.id] = row
        return [merged[key] for key in sorted(merged)]

    def _repository_id_for_project(self, session: Session, project: Project) -> uuid.UUID:
        repository = self._resolve_repository(session, project)
        if repository is None:
            return uuid.UUID(int=0)
        return repository.id

    def _project_evidence(self, session: Session, project: Project) -> Sequence[Evidence]:
        return session.scalars(
            select(Evidence)
            .join(Evidence.task)
            .where(Task.project_id == project.id)
            .order_by(Evidence.id)
        ).all()

    def _protected_behavior_count(self, session: Session, project: Project) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(Behavior)
                .join(Repository, Behavior.repository_id == Repository.id)
                .where(Repository.project_id == project.id, Behavior.protected.is_(True))
            )
            or 0
        )

    def _behavior_count(self, session: Session, repository_id: uuid.UUID) -> int:
        return self._repository_count(session, Behavior, repository_id)

    def _ghost_count(self, session: Session, repository_id: uuid.UUID) -> int:
        return self._repository_count(session, Ghost, repository_id)

    def _repository_count(
        self, session: Session, model: type[Any], repository_id: uuid.UUID
    ) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(model)
                .where(model.repository_id == repository_id)
            )
            or 0
        )

    def _evidence_count(self, session: Session, project: Project) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(Evidence)
                .join(Evidence.task)
                .where(Task.project_id == project.id)
            )
            or 0
        )

    def _constitution_claim_count(self, session: Session, constitution: Constitution) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(ConstitutionClaim)
                .where(ConstitutionClaim.constitution_id == constitution.id)
            )
            or 0
        )

    # -- dto builders ---------------------------------------------------------------------

    def _constitution_dto(
        self, session: Session, constitution: Constitution | None, protected_count: int
    ) -> ConstitutionDto:
        if constitution is None:
            return ConstitutionDto(
                id="", title="", status="DRAFT", protected_count=protected_count
            )
        return ConstitutionDto(
            id=str(constitution.id),
            title=constitution.title,
            version=constitution.version,
            status=constitution.status,
            claim_count=self._constitution_claim_count(session, constitution),
            protected_count=protected_count,
            locked=constitution.locked,
        )

    def _category(self, items: Any) -> FindingsCategory:
        dumped = [item.model_dump(mode="json") for item in items]
        return FindingsCategory(count=len(dumped), items=dumped)

    def _empty_findings(self) -> FindingsSet:
        empty = FindingsCategory(count=0, items=[])
        return FindingsSet(
            behaviors=empty,
            invariants=empty,
            incidents=empty,
            dependencies=empty,
            couplings=empty,
            risk_zones=empty,
            ghosts=empty,
            evidence=empty,
        )

    @staticmethod
    def _make_graph_node(
        index: int,
        *,
        node_id: str,
        object_type: str,
        name: str,
        description: str | None,
        status: str,
        protected: bool | None,
        discovered_at: datetime | None,
        repository_id: str,
        trust_state: str,
    ) -> GraphNodeDto:
        return GraphNodeDto(
            id=node_id,
            type=object_type,
            position={"x": float((index % 4) * 280), "y": float((index // 4) * 180)},
            label=name,
            trust_state=trust_state,
            data=BehavioralObjectDto(
                id=node_id,
                object_type=object_type,
                name=name,
                description=description,
                status=status,
                protected=protected,
                discovered_at=_iso(discovered_at),
                repository_id=repository_id,
                claim_ids=[],
                metadata={},
            ),
        )

    @staticmethod
    def _append_edge(
        edges: list[GraphEdgeDto],
        source: str,
        target: str,
        node_ids: set[str],
        label: str,
    ) -> None:
        if source not in node_ids or target not in node_ids:
            return
        edges.append(
            GraphEdgeDto(
                id=f"{source}->{target}", source=source, target=target, type="animated", label=label
            )
        )

    @staticmethod
    def _trust_state(locked: bool, protected: bool | None, constitution_active: bool) -> str:
        if locked:
            return "LOCKED"
        if protected is True and constitution_active:
            return "PROTECTED"
        return "OBSERVED"


def build_behavior_adapter(
    *,
    database_url: str | None = None,
    auto_seed: bool = True,
    project_id: uuid.UUID | None = None,
) -> BehaviorAdapter:
    """Build a configured ``SqlAlchemyBehaviorAdapter`` over the behavioral DB.

    Resolves the ``database_url`` (defaulting to
    ``DEFAULT_BEHAVIOR_DATABASE_URL``), creates the schema, seeds the
    deterministic demo scenario when ``auto_seed`` is set and the database is
    empty, and returns an adapter bound to a fresh sync session factory.
    """
    url = database_url or DEFAULT_BEHAVIOR_DATABASE_URL
    engine = create_behavior_engine(url)
    ensure_behavior_schema(engine)
    if auto_seed:
        seed_demo_scenario_if_empty(engine)
    factory = behavior_session_factory(engine)
    return SqlAlchemyBehaviorAdapter(factory, project_id=project_id)

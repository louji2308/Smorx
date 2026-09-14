"""Unit tests for the Phase 6 ``SqlAlchemyBehaviorAdapter`` and persistence helpers.

Every test uses a real SQLite file under ``tmp_path``, seeded (or not) through
the same persistence helpers the adapter factory itself calls. Assertions are
grounded in raw counts over the same engine so adapter output is validated
against persisted rows rather than against assumptions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.behavior.adapter import SqlAlchemyBehaviorAdapter, build_behavior_adapter
from app.behavior.contract import ActivateResult, BehaviorContext, FindingsSet
from app.behavior.database import (
    behavior_session_factory,
    create_behavior_engine,
    ensure_behavior_schema,
    seed_demo_scenario_if_empty,
)
from smorx_behavior.models import (
    Behavior,
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
)


def _sqlite_url(tmp_path: Path, name: str) -> str:
    return f"sqlite:///{(tmp_path / name).as_posix()}"


def _table_count(session: Session, model: type[Any]) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_seed_context_is_payments_api(tmp_path: Path) -> None:
    adapter = build_behavior_adapter(database_url=_sqlite_url(tmp_path, "seed.db"))
    ctx = adapter.context()
    assert isinstance(ctx, BehaviorContext)
    assert ctx.project is not None
    assert ctx.project.name == "Payments API"
    assert ctx.project.slug == "payments-api"
    assert ctx.repository is not None
    assert ctx.change is not None
    assert ctx.change.external_id == "184"
    assert ctx.change.title == "AUTH-017 token refresh must reject forged requests"


def test_findings_counts_match_persisted_rows(tmp_path: Path) -> None:
    url = _sqlite_url(tmp_path, "seed.db")
    adapter = build_behavior_adapter(database_url=url)
    engine = create_behavior_engine(url)

    findings = adapter.findings()
    assert isinstance(findings, FindingsSet)
    with Session(engine) as session:
        assert findings.behaviors.count == _table_count(session, Behavior) == 1
        assert findings.ghosts.count == _table_count(session, Ghost) == 1
        assert findings.evidence.count == _table_count(session, Evidence) == 6
        assert findings.invariants.count == _table_count(session, Invariant) == 0
        assert findings.incidents.count == _table_count(session, Incident) == 0
        assert findings.dependencies.count == _table_count(session, Dependency) == 0
        assert findings.risk_zones.count == _table_count(session, RiskZone) == 0

    for category in (
        findings.behaviors,
        findings.invariants,
        findings.incidents,
        findings.dependencies,
        findings.risk_zones,
        findings.ghosts,
        findings.evidence,
    ):
        assert category.count == len(category.items)
    assert findings.couplings.count == 0
    assert findings.couplings.items == []


def test_constitution_seed_db_has_real_protected_count(tmp_path: Path) -> None:
    adapter = build_behavior_adapter(database_url=_sqlite_url(tmp_path, "seed.db"))
    view = adapter.constitution()
    assert view.claims == []
    assert view.version.status == "DRAFT"
    assert view.version.id == ""
    assert view.version.claim_count == 0
    assert view.counts["protected"] == 1


def test_activate_not_drafted_creates_no_row(tmp_path: Path) -> None:
    url = _sqlite_url(tmp_path, "seed.db")
    adapter = build_behavior_adapter(database_url=url)
    engine = create_behavior_engine(url)

    first = adapter.activate()
    assert first.status == "NOT_DRAFTED"
    assert first.message == "no persisted constitution exists to activate; nothing fabricated"
    second = adapter.activate()
    assert second.status == "NOT_DRAFTED"

    with Session(engine) as session:
        assert _table_count(session, Constitution) == 0


def test_activate_transitions_and_is_idempotent(tmp_path: Path) -> None:
    url = _sqlite_url(tmp_path, "seed.db")
    adapter = build_behavior_adapter(database_url=url)
    engine = create_behavior_engine(url)

    with Session(engine) as session:
        project = session.scalars(select(Project).order_by(Project.id)).first()
        assert project is not None
        constitution = Constitution(
            project_id=project.id,
            title="Payments API behavioral constitution",
            statement="Token refresh must reject forged requests.",
            status="DRAFT",
            version=1,
            locked=False,
        )
        session.add(constitution)
        session.flush()
        session.add(
            ConstitutionClaim(
                constitution_id=constitution.id,
                category="GOVERNANCE",
                rule="Token refresh MUST reject forged requests.",
                severity="HIGH",
                position=1,
                locked=False,
            )
        )
        session.commit()

    first = adapter.activate()
    assert isinstance(first, ActivateResult)
    assert first.status == "ACTIVE"
    assert first.claim_count == 1
    assert first.protected_count == 1
    assert first.ratified_at is not None

    second = adapter.activate()
    assert second.status == "ALREADY_ACTIVE"

    view = adapter.constitution()
    assert len(view.claims) == 1
    assert view.version.claim_count == 1
    assert view.version.status == "ACTIVE"
    assert view.claims[0].statement == "Token refresh MUST reject forged requests."
    assert view.claims[0].authority == "GOVERNANCE"

    with Session(engine) as session:
        persisted = session.scalars(
            select(Constitution).where(Constitution.status == "ACTIVE")
        ).one()
        assert persisted.ratified_at is not None
        assert _table_count(session, Constitution) == 1


def test_readiness_seed_db_reports_two_met_steps(tmp_path: Path) -> None:
    adapter = build_behavior_adapter(database_url=_sqlite_url(tmp_path, "seed.db"))
    view = adapter.readiness()
    assert view.total == 4
    assert view.met_count == 2
    assert view.ready is False
    by_id = {step.id: step for step in view.steps}
    assert by_id["archaeology"].met is True
    assert by_id["archaeology"].state == "OBSERVED"
    assert by_id["evidence"].met is True
    assert by_id["constitution"].met is False
    assert by_id["constitution"].state == "UNVERIFIED"
    assert by_id["ratified"].met is False


def test_empty_database_returns_honest_empty_views(tmp_path: Path) -> None:
    url = _sqlite_url(tmp_path, "empty.db")
    adapter = build_behavior_adapter(database_url=url, auto_seed=False)

    ctx = adapter.context()
    assert ctx.project is None
    assert ctx.repository is None
    assert ctx.change is None
    assert ctx.constitution is None

    findings = adapter.findings()
    for category in (
        findings.behaviors,
        findings.invariants,
        findings.incidents,
        findings.dependencies,
        findings.couplings,
        findings.risk_zones,
        findings.ghosts,
        findings.evidence,
    ):
        assert category.count == 0
        assert category.items == []

    graph = adapter.graph()
    assert graph.nodes == []
    assert graph.edges == []

    view = adapter.constitution()
    assert view.claims == []
    assert view.counts["protected"] == 0

    readiness = adapter.readiness()
    assert readiness.met_count == 0
    assert readiness.ready is False

    result = adapter.activate()
    assert result.status == "NOT_DRAFTED"
    assert result.protected_count == 0


def test_seed_demo_scenario_is_idempotent(tmp_path: Path) -> None:
    url = _sqlite_url(tmp_path, "idem.db")
    engine = create_behavior_engine(url)
    ensure_behavior_schema(engine)
    seed_demo_scenario_if_empty(engine)
    seed_demo_scenario_if_empty(engine)
    with Session(engine) as session:
        assert _table_count(session, Project) == 1
        assert _table_count(session, Repository) == 1
        assert _table_count(session, Behavior) == 1
        assert _table_count(session, Ghost) == 1
        assert _table_count(session, Evidence) == 6


def test_graph_nodes_and_replay_edge(tmp_path: Path) -> None:
    adapter = build_behavior_adapter(database_url=_sqlite_url(tmp_path, "seed.db"))
    graph = adapter.graph()

    node_types = {node.type for node in graph.nodes}
    assert node_types == {"BEHAVIOR", "GHOST"}

    behavior_nodes = {node.id for node in graph.nodes if node.type == "BEHAVIOR"}
    ghost_nodes = {node.id for node in graph.nodes if node.type == "GHOST"}
    assert len(behavior_nodes) == 1
    assert len(ghost_nodes) == 1

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.label == "replay"
    assert edge.source in ghost_nodes
    assert edge.target in behavior_nodes

    for node in graph.nodes:
        assert node.data.repository_id
        assert node.data.object_type == node.type
        assert node.data.claim_ids == []
        assert node.trust_state == "OBSERVED"
        if node.type == "BEHAVIOR":
            assert node.data.protected is True
            assert node.data.discovered_at is not None

    positions = {node.id: node.position for node in graph.nodes}
    behavior = next(node for node in graph.nodes if node.type == "BEHAVIOR")
    assert positions[behavior.id] == {"x": 0.0, "y": 0.0}
    assert positions[edge.source] == {"x": 280.0, "y": 0.0}


def test_adapter_session_factory_direct_construction(tmp_path: Path) -> None:
    url = _sqlite_url(tmp_path, "direct.db")
    engine = create_behavior_engine(url)
    ensure_behavior_schema(engine)
    seed_demo_scenario_if_empty(engine)
    adapter = SqlAlchemyBehaviorAdapter(behavior_session_factory(engine))
    ctx = adapter.context()
    assert ctx.project is not None
    assert ctx.project.name == "Payments API"
"""Phase 6 (Discover + Govern) end-to-end integration + honesty verification.

This module is the independent integration test for the parallel adapter
wiring wave. Unlike the unit tests that target the ``BehaviorAdapter``
protocol with fakes, this suite exercises the REAL stack:

- the REAL SQLAlchemy adapter built by ``app.behavior.adapter.build_behavior_adapter``
  pointed at a REAL tmp_path sqlite database seeded with ``build_seed``;
- the REAL HTTP router wiring through ``app.main.create_app`` with a manually
  constructed ``Dependencies`` (mirroring ``tests/test_api.py``) whose
  ``behavior`` slot holds the real adapter;
- REAL persisted rows only (the deterministic Payments API / AUTH-017 fixture).

Honesty invariants asserted here (AGENTS.md sections 3/13/39):

1. Every findings category ``count`` equals ``len(items)``; nothing is padded.
2. Empty categories return ``count == 0`` with ``items == []`` (no fabricated
   placeholder rows inflate the demo narrative).
3. Every evidence item id returned over HTTP is a member of the real
   ``Evidence`` id set persisted in the database.
4. ``POST /behavior/constitution/activate`` against a database with NO
   constitution row returns ``NOT_DRAFTED`` and persists NOTHING (zero
   ``constitutions`` rows remain) - activation must not fabricate a
   constitution to make the demo look governed.
5. After a real ``Constitution`` + ``ConstitutionClaim`` row is provisioned,
   activation transitions that persisted row to ``ACTIVE`` and is idempotent
   (second call returns ``ALREADY_ACTIVE``); the constitution view then
   reflects the persisted claim count, not a hardcoded one.

Dependency on the parallel wave: imports ``app.behavior.adapter`` (agent A)
and ``app.api.behavior_routes`` (agent B). If either module is not yet
landed this file fails at collection time with a ``ModuleNotFoundError``; that
is the intended honest signal and the orchestrator re-runs after the wave.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.behavior_routes import create_behavior_router  # noqa: F401  (agent B artifact)
from app.behavior.adapter import build_behavior_adapter  # agent A artifact
from app.deps import Dependencies
from app.main import create_app
from app.model.nemotron import NemotronModelService
from app.model.router import ModelRouter
from app.runtime.proof import ProofPathService
from app.runtime.service import AgentRuntime
from app.settings import Settings
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Constitution, ConstitutionClaim, Evidence, Project
from smorx_behavior.seed.demo import build_seed
from tests.conftest import FakeSandbox, FakeTokenFactoryClient

PATCH = {"x": 0, "y": 0}

CONSTITUTION_TOKEN = "integration/constitution/payments-api"
CLAIM_RULE = "The token-refresh endpoint MUST reject forged requests."


def _url_for(db_path) -> str:
    return "sqlite:///" + str(db_path).replace("\\", "/")


@pytest.fixture(scope="module")
def app_ctx(tmp_path_factory):
    """Seed a fresh DB, build the REAL adapter + REAL app wiring, patch deps."""
    db_path = tmp_path_factory.mktemp("behavior_integration") / "integration.sqlite"
    db_url = _url_for(db_path)
    engine = create_sync_engine(db_url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        report = build_seed(session)

    adapter = build_behavior_adapter(database_url=db_url, auto_seed=False, project_id=None)

    settings = Settings()
    fake_client = FakeTokenFactoryClient(
        content="INFRA_OK", model=settings.nemotron_model_nano
    )
    model_router = ModelRouter(settings=settings)
    model_service = NemotronModelService(
        client=fake_client, router=model_router, settings=settings
    )
    sandbox = FakeSandbox()
    runtime = AgentRuntime(settings=settings, model_service=model_service, sandbox=sandbox)
    proof = ProofPathService(settings=settings, model_service=model_service, sandbox=sandbox)
    deps = Dependencies(
        settings=settings,
        model_client=fake_client,
        model_router=model_router,
        model_service=model_service,
        sandbox=sandbox,
        runtime=runtime,
        proof=proof,
        behavior=adapter,
    )

    patch = pytest.MonkeyPatch()
    patch.setattr("app.main.build_dependencies", lambda settings=None: deps)
    try:
        with TestClient(create_app(settings)) as client:
            yield {
                "client": client,
                "engine": engine,
                "db_url": db_url,
                "adapter": adapter,
                "report": report,
            }
    finally:
        patch.undo()


def test_context_is_derived_from_real_seeded_rows(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    response = client.get("/api/v1/behavior/context")
    assert response.status_code == 200
    body = response.json()
    assert body["project"] is not None
    assert body["project"]["name"] == "Payments API"
    assert body["project"]["slug"] == "payments-api"
    assert body["change"] is not None
    assert body["change"]["external_id"] == "184"
    assert body["repository"] is not None
    assert body["repository"]["name"] == "smorx/payments-api"
    assert body["constitution"] is not None
    assert body["constitution"]["id"] == ""
    assert body["constitution"]["status"] == "DRAFT"


def test_findings_match_seeded_rows_and_empty_categories_are_empty(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    report = app_ctx["report"]
    response = client.get("/api/v1/behavior/findings")
    assert response.status_code == 200
    body = response.json()

    for category in ("invariants", "incidents", "dependencies", "couplings", "risk_zones"):
        assert body[category] == {"count": 0, "items": []}, category

    assert body["behaviors"]["count"] == 1
    behavior = body["behaviors"]["items"][0]
    assert behavior["id"] == str(report.behavior_id)
    assert behavior["name"] == "auth token refresh"

    assert body["ghosts"]["count"] == 1
    ghost = body["ghosts"]["items"][0]
    assert ghost["id"] == str(report.ghost_id)

    assert body["evidence"]["count"] == 6


def test_graph_nodes_edges_and_positions_are_consistent(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    response = client.get("/api/v1/behavior/graph")
    assert response.status_code == 200
    body = response.json()

    node_ids = [node["id"] for node in body["nodes"]]
    node_types = {node["type"] for node in body["nodes"]}
    assert "BEHAVIOR" in node_types
    assert "GHOST" in node_types

    id_set = set(node_ids)
    for edge in body["edges"]:
        assert edge["source"] in id_set, edge
        assert edge["target"] in id_set, edge

    for node in body["nodes"]:
        position = node["position"]
        assert isinstance(position["x"], (int, float)), node
        assert isinstance(position["y"], (int, float)), node
        # NaN would silently poison layout; the contract type is float, so
        # whole-number values are emitted as e.g. ``0.0`` by JSON.
        assert position["x"] == position["x"], node
        assert position["y"] == position["y"], node


def test_constitution_placeholder_is_honest_when_nothing_seeded(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    response = client.get("/api/v1/behavior/constitution")
    assert response.status_code == 200
    body = response.json()
    assert body["version"]["claim_count"] == 0
    assert body["claims"] == []
    assert body["counts"]["protected"] == 1
    assert body["counts"]["observed"] == 0


def test_readiness_reports_not_ready_with_only_seeded_data(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    response = client.get("/api/v1/behavior/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert body["met_count"] == 2
    constitution_steps = [
        step
        for step in body["steps"]
        if "constitution" in (step["id"] + step["label"]).lower()
    ]
    assert constitution_steps, "no step references the constitution; contract deviation"
    assert all(step["met"] is False for step in constitution_steps)


def test_activation_does_not_fabricate_when_no_constitution_exists(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    engine = app_ctx["engine"]
    response = client.post("/api/v1/behavior/constitution/activate")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NOT_DRAFTED"
    with Session(engine) as session:
        rows = session.execute(select(Constitution)).scalars().all()
    assert rows == []


def _provision_constitution(engine) -> uuid.UUID:
    ns = uuid.NAMESPACE_URL
    with Session(engine) as session:
        project = session.execute(select(Project)).scalars().first()
        assert project is not None
        constitution = Constitution(
            id=uuid.uuid5(ns, CONSTITUTION_TOKEN),
            project_id=project.id,
            title="Payments API behavior constitution",
            statement="Governance source of truth for Payments API.",
            status="DRAFT",
            owner_scope="GOVERNANCE",
            version=1,
            locked=False,
        )
        session.add(constitution)
        claim = ConstitutionClaim(
            id=uuid.uuid5(ns, CONSTITUTION_TOKEN + "/claim"),
            constitution_id=constitution.id,
            category="SECURITY",
            rule=CLAIM_RULE,
            severity="HIGH",
            position=1,
            version=1,
            locked=False,
        )
        session.add(claim)
        session.commit()
        return constitution.id


def test_activation_is_active_and_idempotent_after_real_provision(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    provision_id = _provision_constitution(app_ctx["engine"])

    first = client.post("/api/v1/behavior/constitution/activate")
    assert first.status_code == 200
    assert first.json()["status"] == "ACTIVE"

    second = client.post("/api/v1/behavior/constitution/activate")
    assert second.status_code == 200
    assert second.json()["status"] == "ALREADY_ACTIVE"

    with Session(app_ctx["engine"]) as session:
        consistency = {
            r[0]: r[1]
            for r in session.execute(select(Constitution.id, Constitution.status)).all()
        }
    assert consistency.get(provision_id) == "ACTIVE"


def test_constitution_view_reflects_persisted_claim(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    response = client.get("/api/v1/behavior/constitution")
    assert response.status_code == 200
    body = response.json()
    assert body["version"]["claim_count"] == 1
    assert len(body["claims"]) == 1
    assert body["claims"][0]["statement"] == CLAIM_RULE


def test_honesty_counts_equal_item_lengths(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    response = client.get("/api/v1/behavior/findings")
    assert response.status_code == 200
    body = response.json()
    categories = (
        "behaviors",
        "invariants",
        "incidents",
        "dependencies",
        "couplings",
        "risk_zones",
        "ghosts",
        "evidence",
    )
    for category in categories:
        assert body[category]["count"] == len(body[category]["items"]), category


def test_evidence_items_are_subset_of_persisted_evidence_ids(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    engine = app_ctx["engine"]
    with Session(engine) as session:
        real_ids = {str(r) for r in session.execute(select(Evidence.id)).scalars()}
    assert len(real_ids) == 6

    response = client.get("/api/v1/behavior/findings")
    assert response.status_code == 200
    body = response.json()
    item_ids = [item["id"] for item in body["evidence"]["items"]]
    for item_id in item_ids:
        assert item_id in real_ids, f"fabricated evidence item id {item_id!r}"


def test_dto_shapes_are_stable(app_ctx) -> None:
    client: TestClient = app_ctx["client"]
    findings = client.get("/api/v1/behavior/findings").json()
    behavior = findings["behaviors"]["items"][0]
    assert behavior["type"] == "BEHAVIOR"
    assert set(behavior) >= {"id", "name", "type", "status", "protected", "evidence_count"}

    ghost = findings["ghosts"]["items"][0]
    assert ghost["type"] == "GHOST"

    constitution = client.get("/api/v1/behavior/constitution").json()
    assert set(constitution["version"]) >= {"id", "version", "status", "claim_count"}
    assert isinstance(constitution["counts"], dict)

    readiness = client.get("/api/v1/behavior/readiness").json()
    for step in readiness["steps"]:
        assert set(step) >= {"id", "label", "state", "met"}
    assert readiness["total"] == len(readiness["steps"])
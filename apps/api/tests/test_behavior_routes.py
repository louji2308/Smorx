from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.behavior_routes import create_behavior_router
from app.behavior.contract import (
    ActivateResult,
    BehavioralObjectDto,
    BehaviorContext,
    ChangeDto,
    ClaimDto,
    ConstitutionDto,
    ConstitutionVersionDto,
    ConstitutionView,
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


class FakeBehaviorAdapter:
    """Pure-in-Python ``BehaviorAdapter`` returning concrete contract DTOs (no DB)."""

    def __init__(self) -> None:
        self.activate_calls = 0
        self.fail_on: str | None = None

    def context(self) -> BehaviorContext:
        self._maybe_fail("context")
        return BehaviorContext(
            project=ProjectDto(id="p1", name="Smorx", slug="smorx"),
            repository=RepositoryDto(id="r1", name="smorx-behavior"),
            change=ChangeDto(id="c1", title="Wire behavior API", status="OPEN"),
            constitution=ConstitutionDto(
                id="p1",
                title="Behavioral Constitution",
                version=1,
                status="DRAFT",
                claim_count=2,
                protected_count=1,
            ),
        )

    def findings(self) -> FindingsSet:
        self._maybe_fail("findings")
        behaviors = [
            {"id": "f-1", "name": "session persistence", "type": "BEHAVIOR", "status": "OBSERVED"},
            {"id": "f-2", "name": "auth retry loop", "type": "BEHAVIOR", "status": "CONFIRMED"},
        ]
        return FindingsSet(
            behaviors=self._category(behaviors),
            invariants=self._category([]),
            incidents=self._category([]),
            dependencies=self._category([]),
            couplings=self._category([]),
            risk_zones=self._category([]),
            ghosts=self._category([]),
            evidence=self._category([]),
        )

    def graph(self) -> GraphDto:
        self._maybe_fail("graph")
        node = GraphNodeDto(
            id="n1",
            type="BEHAVIOR",
            position={"x": 0.0, "y": 0.0},
            label="Session persistence",
            trust_state="OBSERVED",
            data=BehavioralObjectDto(
                id="o1",
                object_type="BEHAVIOR",
                name="session persistence",
                repository_id="r1",
            ),
        )
        return GraphDto(nodes=[node], edges=[GraphEdgeDto(id="e1", source="n1", target="n2")])

    def constitution(self) -> ConstitutionView:
        self._maybe_fail("constitution")
        version = ConstitutionVersionDto(
            id="p1",
            version=1,
            title="Behavioral Constitution",
            status="DRAFT",
            claim_count=2,
            protected_count=1,
        )
        claim = ClaimDto(
            id="cl-1",
            claim_id="claim-1",
            statement="session persistence is required",
            authority="smorx-behavior",
            status="OBSERVED",
            created_at="2026-01-01T00:00:00Z",
        )
        return ConstitutionView(
            version=version,
            claims=[claim],
            counts={"protected": 1, "observed": 2, "hypotheses": 0, "conflicts": 0},
        )

    def readiness(self) -> ReadinessView:
        self._maybe_fail("readiness")
        steps = [
            ReadinessStepDto(id="s1", label="constitution drafted", state="VERIFIED", met=True),
            ReadinessStepDto(id="s2", label="constitution ratified", state="FAILED", met=False),
        ]
        return ReadinessView(steps=steps, met_count=1, total=2, ready=False)

    def activate(self) -> ActivateResult:
        self._maybe_fail("activate")
        self.activate_calls += 1
        return ActivateResult(
            status="ACTIVE",
            constitution=ConstitutionDto(
                id="p1",
                title="Behavioral Constitution",
                version=1,
                status="ACTIVE",
                claim_count=2,
                protected_count=1,
                locked=True,
            ),
            claim_count=2,
            protected_count=1,
            ratified_at="2026-01-01T00:00:00Z",
            message="activated",
        )

    def _category(self, items: list[dict[str, Any]]) -> FindingsCategory:
        return FindingsCategory(count=len(items), items=items)

    def _maybe_fail(self, method: str) -> None:
        if self.fail_on == method:
            raise RuntimeError("boom")


def _make_client(adapter: FakeBehaviorAdapter) -> TestClient:
    app = FastAPI()
    app.include_router(create_behavior_router(adapter))
    return TestClient(app)


def test_context_endpoint_returns_project_and_governing_shape() -> None:
    fake = FakeBehaviorAdapter()
    with _make_client(fake) as client:
        response = client.get("/api/v1/behavior/context")
    assert response.status_code == 200
    body = response.json()
    assert body["project"]["name"] == "Smorx"
    assert body["project"]["slug"] == "smorx"
    assert body["repository"]["name"] == "smorx-behavior"
    assert body["change"]["id"] == "c1"
    assert body["constitution"]["status"] == "DRAFT"


def test_findings_endpoint_returns_counts_and_empty_categories() -> None:
    fake = FakeBehaviorAdapter()
    with _make_client(fake) as client:
        response = client.get("/api/v1/behavior/findings")
    assert response.status_code == 200
    body = response.json()
    assert body["behaviors"]["count"] == 2
    assert len(body["behaviors"]["items"]) == 2
    assert body["invariants"]["count"] == 0
    assert body["invariants"]["items"] == []
    assert body["couplings"]["count"] == 0
    assert body["couplings"]["items"] == []
    assert body["evidence"]["items"] == []


def test_graph_endpoint_returns_nodes_and_edges() -> None:
    fake = FakeBehaviorAdapter()
    with _make_client(fake) as client:
        response = client.get("/api/v1/behavior/graph")
    assert response.status_code == 200
    body = response.json()
    assert len(body["nodes"]) == 1
    assert len(body["edges"]) == 1
    assert body["nodes"][0]["label"] == "Session persistence"
    assert body["nodes"][0]["data"]["object_type"] == "BEHAVIOR"


def test_constitution_endpoint_returns_version_claims_counts() -> None:
    fake = FakeBehaviorAdapter()
    with _make_client(fake) as client:
        response = client.get("/api/v1/behavior/constitution")
    assert response.status_code == 200
    body = response.json()
    assert body["version"]["version"] == 1
    assert body["version"]["title"] == "Behavioral Constitution"
    assert len(body["claims"]) == 1
    assert body["claims"][0]["claim_id"] == "claim-1"
    assert body["counts"]["protected"] == 1
    assert body["counts"]["observed"] == 2


def test_readiness_endpoint_returns_ready_and_counts() -> None:
    fake = FakeBehaviorAdapter()
    with _make_client(fake) as client:
        response = client.get("/api/v1/behavior/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert body["met_count"] == 1
    assert body["total"] == 2
    assert len(body["steps"]) == 2
    assert body["steps"][0]["met"] is True


def test_activate_endpoint_calls_adapter_once() -> None:
    fake = FakeBehaviorAdapter()
    with _make_client(fake) as client:
        response = client.post("/api/v1/behavior/constitution/activate")
    assert response.status_code == 200
    assert fake.activate_calls == 1
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["constitution"]["status"] == "ACTIVE"


def test_activate_is_repeatable_and_records_both_calls() -> None:
    fake = FakeBehaviorAdapter()
    with _make_client(fake) as client:
        first = client.post("/api/v1/behavior/constitution/activate")
        second = client.post("/api/v1/behavior/constitution/activate")
    assert first.status_code == 200
    assert second.status_code == 200
    assert fake.activate_calls == 2
    assert second.json()["status"] == "ACTIVE"


def test_adapter_failure_returns_behavior_500() -> None:
    fake = FakeBehaviorAdapter()
    fake.fail_on = "context"
    with _make_client(fake) as client:
        response = client.get("/api/v1/behavior/context")
    assert response.status_code == 500
    assert response.json() == {"category": "behavior", "message": "internal error"}

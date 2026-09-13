from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.deps import Dependencies
from app.main import create_app
from app.model.nemotron import NemotronModelService
from app.model.router import ModelRouter
from app.runtime.proof import ProofPathService
from app.runtime.service import AgentRuntime
from app.settings import Settings
from tests.conftest import FakeSandbox, FakeTokenFactoryClient


def _build_app(settings: Settings | None = None) -> TestClient:
    resolved = settings if settings is not None else Settings()
    return TestClient(create_app(settings=resolved))


def test_root_endpoint() -> None:
    with _build_app() as client:
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Smorx API"
        assert body["phase"] == "1-infrastructure"
        assert body["version"] == "0.1.0"


def test_health_endpoint() -> None:
    with _build_app() as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_docs_exposed_in_development() -> None:
    with _build_app() as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_docs_hidden_in_production() -> None:
    resolved = Settings(app_env="production")
    with _build_app(resolved) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_infra_status_reports_unhealthy_without_credentials() -> None:
    with _build_app() as client:
        response = client.get("/api/v1/infra/status")
        assert response.status_code == 200
        body = response.json()
        assert body["liveness"] == "ok"
        assert body["inference"]["configured"] is False
        assert body["inference"]["status"] == "unhealthy"
        assert body["sandbox"]["configured"] is False
        assert body["sandbox"]["status"] == "unhealthy"


def test_proof_returns_503_without_credentials() -> None:
    with _build_app() as client:
        response = client.post("/api/v1/infra/proof")
        assert response.status_code == 503
        body = response.json()
        assert body["category"] == "configuration_failure"
        assert "NEBIUS_API_KEY" in body["message"]
        assert "remediation" in body


def test_proof_succeeds_with_injected_fakes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        nebius_api_key="k",
        nebius_ai_project="p",
        nemotron_model_nano="model-nano",
        nemotron_model_super="model-super",
        nemotron_model_ultra="model-ultra",
        command_timeout_seconds=10.0,
    )
    client = FakeTokenFactoryClient(content="INFRA_OK", model=settings.nemotron_model_nano)
    router = ModelRouter(settings=settings)
    service = NemotronModelService(client=client, router=router, settings=settings)
    sandbox = FakeSandbox()
    runtime = AgentRuntime(settings=settings, model_service=service, sandbox=sandbox)
    proof = ProofPathService(settings=settings, model_service=service, sandbox=sandbox)
    deps = Dependencies(
        settings=settings,
        model_client=client,
        model_router=router,
        model_service=service,
        sandbox=sandbox,
        runtime=runtime,
        proof=proof,
    )

    def fake_build_dependencies(_settings: Settings | None = None) -> Dependencies:
        return deps

    monkeypatch.setattr("app.main.build_dependencies", fake_build_dependencies)
    with _build_app(settings) as http:
        status = http.get("/api/v1/infra/status")
        assert status.status_code == 200
        status_body = status.json()
        assert status_body["inference"]["configured"] is True
        assert status_body["inference"]["status"] == "healthy"
        assert status_body["sandbox"]["configured"] is True
        assert status_body["sandbox"]["status"] == "healthy"

        response = http.post("/api/v1/infra/proof")
        assert response.status_code == 200
        body = response.json()
        assert body["machine_verifiable"] is True
        assert body["model_participated"] is True
        assert body["execution_authoritative"] is True
        assert body["routing"]["selected_model"] == "model-nano"
        assert body["sandbox"]["base_image"] == settings.sandbox_base_image
        assert body["command_result"]["exit_code"] == 0
        assert body["command_result"]["status"] == "succeeded"

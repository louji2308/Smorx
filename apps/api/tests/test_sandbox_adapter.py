from __future__ import annotations

import pytest
from contree_sdk.sdk.exceptions import ContreeImageNotFoundError  # type: ignore[import-untyped]

from app.contracts import HealthStatus, SandboxExecutionPort
from app.errors import ConfigurationError, FailureCategory
from app.providers.sandbox.adapter import ContreeSandboxAdapter
from app.settings import Settings


def test_adapter_requires_api_key() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        ContreeSandboxAdapter(settings=Settings())
    assert exc_info.value.category is FailureCategory.CONFIGURATION
    assert "NEBIUS_API_KEY" in str(exc_info.value)


def test_adapter_requires_project() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        ContreeSandboxAdapter(settings=Settings(nebius_api_key="t"))
    assert "NEBIUS_AI_PROJECT" in str(exc_info.value)


def test_adapter_with_credentials_implements_port() -> None:
    adapter = ContreeSandboxAdapter(
        settings=Settings(nebius_api_key="t", nebius_ai_project="p")
    )
    assert isinstance(adapter, SandboxExecutionPort)
    for method in (
        "create_sandbox",
        "run_command",
        "read_file",
        "write_file",
        "list_files",
        "checkpoint",
        "rollback",
        "destroy",
        "health",
    ):
        assert callable(getattr(adapter, method)), f"missing port method: {method}"


def test_adapter_credentials_via_project_id_fallback() -> None:
    adapter = ContreeSandboxAdapter(
        settings=Settings(nebius_api_key="t", nebius_project_id="pid")
    )
    assert isinstance(adapter, SandboxExecutionPort)


async def test_health_reports_degraded_when_probe_image_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = ContreeSandboxAdapter(
        settings=Settings(nebius_api_key="t", nebius_ai_project="p")
    )

    def fake_use(ref: str, strict: bool = False) -> object:
        raise ContreeImageNotFoundError("image not provisioned")

    monkeypatch.setattr(adapter._client.images, "use", fake_use)
    report = await adapter.health()
    assert report.status is HealthStatus.DEGRADED
    assert report.models_verified == ["python:3.11-slim"]

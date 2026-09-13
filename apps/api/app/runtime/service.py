from __future__ import annotations

from typing import Any

from app.contracts import HealthStatus, SandboxExecutionPort
from app.errors import ConfigurationError
from app.runtime.proof import ModelServicePort
from app.settings import Settings


class AgentRuntime:
    """Composite runtime facade exposing real provider health without crashing."""

    def __init__(
        self,
        settings: Settings,
        model_service: ModelServicePort | None = None,
        sandbox: SandboxExecutionPort | None = None,
    ) -> None:
        self._settings = settings
        self._model_service = model_service
        self._sandbox = sandbox

    def _resolve_model_service(self) -> ModelServicePort:
        if self._model_service is None:
            from app.deps import build_model_service

            self._model_service = build_model_service(self._settings)
        return self._model_service

    def _resolve_sandbox(self) -> SandboxExecutionPort:
        if self._sandbox is None:
            from app.deps import build_sandbox

            self._sandbox = build_sandbox(self._settings)
        return self._sandbox

    async def health(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "app_env": self._settings.app_env,
            "liveness": "ok",
        }
        result["inference"] = await self._probe_model()
        result["sandbox"] = await self._probe_sandbox()
        return result

    async def _probe_model(self) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "configured": self._settings.has_inference_credentials,
            "provider": "nebius_token_factory",
            "status": HealthStatus.UNHEALTHY.value,
            "latency_ms": None,
            "detail": "",
        }
        try:
            report = await self._resolve_model_service().health()
        except ConfigurationError as exc:
            summary["detail"] = exc.message
            return summary
        summary["status"] = report.status.value
        summary["latency_ms"] = report.latency_ms
        summary["detail"] = report.detail or ""
        summary["models_verified"] = list(report.models_verified)
        return summary

    async def _probe_sandbox(self) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "configured": self._settings.has_sandbox_credentials,
            "provider": "nebius_contree",
            "status": HealthStatus.UNHEALTHY.value,
            "latency_ms": None,
            "detail": "",
        }
        try:
            report = await self._resolve_sandbox().health()
        except ConfigurationError as exc:
            summary["detail"] = exc.message
            return summary
        summary["status"] = report.status.value
        summary["latency_ms"] = report.latency_ms
        summary["detail"] = report.detail or ""
        return summary

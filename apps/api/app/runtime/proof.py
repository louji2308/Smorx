from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from app.contracts import (
    CommandRequest,
    CommandResult,
    ExecutionStatus,
    ModelCompletion,
    ModelRequest,
    ModelResponse,
    ProviderHealthReport,
    RoutingDecision,
    Sandbox,
    SandboxExecutionPort,
)
from app.observability import new_id
from app.settings import Settings


@runtime_checkable
class ModelServicePort(Protocol):
    """Minimal contract a proof path needs from the model service."""

    async def complete(self, request: ModelRequest) -> ModelCompletion: ...

    async def health(self) -> ProviderHealthReport: ...


class ProofResult(BaseModel):
    """Evidence-bound record of one full infrastructure proof run."""

    request_id: str
    routing: RoutingDecision
    model_response: ModelResponse
    sandbox: Sandbox
    command_result: CommandResult
    model_participated: bool
    execution_authoritative: bool
    machine_verifiable: bool
    timestamp: datetime


class ProofPathService:
    """Runs the real model -> sandbox -> command evidence path with no fabrication."""

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

    async def execute(self) -> ProofResult:
        settings = self._settings
        model_service = self._resolve_model_service()
        adapter = self._resolve_sandbox()
        timestamp = datetime.now(UTC)
        request = ModelRequest(
            model=settings.nemotron_model_nano,
            system="You are the infrastructure validator. Reply with exactly: INFRA_OK",
            prompt="Confirm the sandbox executed and you are online. Reply with exactly: INFRA_OK",
            request_id=new_id("req"),
            run_id=new_id("run"),
            timestamp=timestamp,
        )
        model_completion = await model_service.complete(request)
        sandbox = await adapter.create_sandbox(settings.sandbox_base_image)
        command_result = await adapter.run_command(
            sandbox.sandbox_id,
            CommandRequest(
                command="echo INFRA_OK && python3 --version",
                shell=True,
                disposable=True,
                timeout_seconds=settings.command_timeout_seconds,
            ),
        )
        execution_authoritative = (
            command_result.status == ExecutionStatus.SUCCEEDED and command_result.exit_code == 0
        )
        model_participated = model_completion.response.content.strip().upper() == "INFRA_OK"
        return ProofResult(
            request_id=request.request_id,
            routing=model_completion.routing,
            model_response=model_completion.response,
            sandbox=sandbox,
            command_result=command_result,
            model_participated=model_participated,
            execution_authoritative=execution_authoritative,
            machine_verifiable=execution_authoritative and model_participated,
            timestamp=timestamp,
        )

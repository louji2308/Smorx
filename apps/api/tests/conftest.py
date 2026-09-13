from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from app.contracts import (
    Checkpoint,
    CommandRequest,
    CommandResult,
    ExecutionStatus,
    FileEntry,
    HealthStatus,
    ModelRequest,
    ModelResponse,
    ProviderHealthReport,
    RollbackResult,
    Sandbox,
    SandboxState,
    TokenUsage,
)
from app.observability import new_id
from app.providers.sandbox.port import SANDBOX_PROVIDER
from app.providers.token_factory.client import PROVIDER as TOKEN_FACTORY_PROVIDER
from app.settings import Settings, get_settings


def _now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    for env_name in list(os.environ):
        if env_name.upper().startswith(("NEBIUS_", "CONTREE_")):
            monkeypatch.delenv(env_name, raising=False)


@pytest.fixture
def settings() -> Settings:
    return Settings()


class FakeTokenFactoryClient:
    """Offline stand-in for the Token Factory OpenAI-compatible adapter."""

    def __init__(
        self,
        content: str = "INFRA_OK",
        *,
        model: str = "test-model",
        usage: TokenUsage | None = None,
        health_report: ProviderHealthReport | None = None,
    ) -> None:
        self.content = content
        self.model = model
        self.usage = usage
        self.health_report = health_report or ProviderHealthReport(
            provider=TOKEN_FACTORY_PROVIDER,
            status=HealthStatus.HEALTHY,
            latency_ms=1,
            checked_at=_now(),
            models_verified=[model],
        )
        self.last_request: ModelRequest | None = None
        self.chat_completion_calls: int = 0

    async def chat_completion(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        self.chat_completion_calls += 1
        return ModelResponse(
            id="chatcmpl-fake",
            model=request.model,
            provider=TOKEN_FACTORY_PROVIDER,
            content=self.content,
            finish_reason="stop",
            usage=self.usage
            or TokenUsage(prompt_tokens=10, completion_tokens=4, total_tokens=14),
            duration_ms=1,
            created_at=_now(),
            request_id=request.request_id,
            run_id=request.run_id,
        )

    async def list_models(self) -> list[str]:
        return [self.model]

    async def health(self, model: str | None = None) -> ProviderHealthReport:
        return self.health_report


class FakeSandbox:
    """In-memory ``SandboxExecutionPort`` implementation for offline tests."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.command_results: list[CommandResult] = []
        self.sandboxes: dict[str, Sandbox] = {}
        self.checkpoints: dict[str, Checkpoint] = {}
        self.destroyed: list[str] = []
        self.created_order: list[str] = []
        self.last_created_base_image: str | None = None
        self.last_command_request: CommandRequest | None = None

    async def create_sandbox(
        self,
        base_image: str,
        *,
        tag: str | None = None,
        label: str | None = None,
    ) -> Sandbox:
        sandbox = Sandbox(
            sandbox_id=new_id("sbox"),
            state=SandboxState.READY,
            base_image=base_image,
            created_at=_now(),
            current_tag=tag,
        )
        self.sandboxes[sandbox.sandbox_id] = sandbox
        self.created_order.append(sandbox.sandbox_id)
        self.last_created_base_image = base_image
        return sandbox

    async def run_command(
        self,
        sandbox_id: str,
        request: CommandRequest,
    ) -> CommandResult:
        self.last_command_request = request
        if self.command_results:
            return self.command_results.pop(0)
        return default_command_result(sandbox_id, request)

    async def read_file(self, sandbox_id: str, path: str) -> bytes:
        return self.files.get(path, b"")

    async def write_file(
        self,
        sandbox_id: str,
        path: str,
        content: str | bytes,
    ) -> str:
        self.files[path] = content.encode() if isinstance(content, str) else content
        return new_id("state")

    async def list_files(self, sandbox_id: str, path: str = "/") -> list[FileEntry]:
        return [
            FileEntry(path=file_path, size=len(data), is_dir=False)
            for file_path, data in self.files.items()
        ]

    async def checkpoint(self, sandbox_id: str, label: str | None = None) -> Checkpoint:
        checkpoint = Checkpoint(
            checkpoint_id=new_id("ckpt"),
            label=label,
            created_at=_now(),
            sandbox_id=sandbox_id,
        )
        self.checkpoints[checkpoint.checkpoint_id] = checkpoint
        return checkpoint

    async def rollback(self, sandbox_id: str, checkpoint_id: str) -> RollbackResult:
        return RollbackResult(
            previous_checkpoint_id=sandbox_id,
            restored_checkpoint_id=checkpoint_id,
            restored_at=_now(),
            message="restored",
        )

    async def destroy(self, sandbox_id: str) -> bool:
        if sandbox_id not in self.sandboxes:
            return False
        self.destroyed.append(sandbox_id)
        self.sandboxes.pop(sandbox_id, None)
        return True

    async def health(self) -> ProviderHealthReport:
        return ProviderHealthReport(
            provider=SANDBOX_PROVIDER,
            status=HealthStatus.HEALTHY,
            latency_ms=1,
            checked_at=_now(),
        )


def make_model_request(
    model: str = "coding",
    *,
    prompt: str = "write a function that returns a sorted list",
    system: str | None = "be brief",
    request_id: str = "req-1",
    run_id: str | None = "run-1",
) -> ModelRequest:
    return ModelRequest(
        model=model,
        system=system,
        prompt=prompt,
        request_id=request_id,
        run_id=run_id,
        timestamp=_now(),
    )


def default_command_result(
    sandbox_id: str,
    request: CommandRequest,
    *,
    exit_code: int = 0,
) -> CommandResult:
    status = ExecutionStatus.SUCCEEDED if exit_code == 0 else ExecutionStatus.FAILED
    return CommandResult(
        exit_code=exit_code,
        stdout="INFRA_OK\n" if exit_code == 0 else "",
        stderr="" if exit_code == 0 else "command failed",
        duration_ms=5,
        status=status,
        command=request.command,
        working_directory=request.working_directory,
        environment=dict(request.environment),
        sandbox_id=sandbox_id,
        correlation_id=request.correlation_id,
        truncated=False,
        timestamp=_now(),
        provider=SANDBOX_PROVIDER,
    )


def make_command_result(
    *,
    exit_code: int = 0,
    stdout: str = "out\n",
    stderr: str = "",
    status: ExecutionStatus | None = None,
    command: str = "echo ok",
    sandbox_id: str | None = None,
) -> CommandResult:
    return CommandResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_ms=5,
        status=status
        or (ExecutionStatus.SUCCEEDED if exit_code == 0 else ExecutionStatus.FAILED),
        command=command,
        sandbox_id=sandbox_id,
        truncated=False,
        timestamp=_now(),
        provider=SANDBOX_PROVIDER,
    )

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────

class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"


class SandboxState(StrEnum):
    CREATED = "created"
    READY = "ready"
    BUSY = "busy"
    EXECUTING = "executing"
    TERMINATED = "terminated"
    ERRORED = "errored"


class TaskClass(StrEnum):
    SIMPLE = "simple"
    NORMAL = "normal"
    HARD = "hard"


class ModelTier(StrEnum):
    NANO = "nano"
    SUPER = "super"
    ULTRA = "ultra"


class RoutingCapability(StrEnum):
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    ROUTINE_DECISION = "routine_decision"
    CODING = "coding"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    SYNTHESIS = "synthesis"
    CERTIFICATION = "certification"


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# ── Token usage (model response metadata) ────────────────────────────────────

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


# ── Model request / response ─────────────────────────────────────────────────

class ModelRequest(BaseModel):
    model: str
    system: str | None = None
    prompt: str
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: dict[str, object] | None = None
    request_id: str
    run_id: str | None = None
    timestamp: datetime


class ModelResponse(BaseModel):
    id: str
    model: str
    provider: str = "nebius_token_factory"
    content: str
    finish_reason: str | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    duration_ms: int
    created_at: datetime
    request_id: str
    run_id: str | None = None


# ── Model routing ─────────────────────────────────────────────────────────────

class RoutingDecision(BaseModel):
    selected_model: str
    tier: ModelTier
    reason: str
    task_class: TaskClass
    capability: RoutingCapability
    confidence: float = 1.0
    context_tokens: int = 0
    latency_sensitive: bool = False
    criticality: str = "normal"
    timestamp: datetime
    run_id: str | None = None


class ModelCompletion(BaseModel):
    response: ModelResponse
    routing: RoutingDecision


# ── Sandbox / execution ───────────────────────────────────────────────────────

class CommandRequest(BaseModel):
    command: str
    shell: bool = True
    args: list[str] | None = None
    working_directory: str | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float | None = None
    files: dict[str, str | bytes] | None = None
    stdin: str | bytes | None = None
    disposable: bool = False
    truncate_output_at: int | None = None
    preserve_env: bool = False
    tag: str | None = None
    correlation_id: str | None = None


class CommandResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    status: ExecutionStatus
    command: str
    working_directory: str | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    sandbox_id: str | None = None
    checkpoint_id: str | None = None
    correlation_id: str | None = None
    truncated: bool = False
    timestamp: datetime
    provider: str = "nebius_contree"


class FileEntry(BaseModel):
    path: str
    size: int
    is_dir: bool = False
    mode: int | None = None


class Sandbox(BaseModel):
    sandbox_id: str
    state: SandboxState
    base_image: str
    created_at: datetime
    current_tag: str | None = None


class Checkpoint(BaseModel):
    checkpoint_id: str
    label: str | None = None
    created_at: datetime
    sandbox_id: str | None = None


class RollbackResult(BaseModel):
    previous_checkpoint_id: str
    restored_checkpoint_id: str
    restored_at: datetime
    message: str = ""


# ── Provider health ───────────────────────────────────────────────────────────

class ProviderHealthReport(BaseModel):
    provider: str
    status: HealthStatus
    latency_ms: int | None = None
    checked_at: datetime
    detail: str = ""
    models_verified: list[str] = Field(default_factory=list)


# ── SandboxExecutionPort (the application abstraction) ───────────────────────

@runtime_checkable
class SandboxExecutionPort(Protocol):
    """Port that the rest of the application depends on.

    Every sandbox provider adapter must implement this protocol.
    """

    async def create_sandbox(
        self,
        base_image: str,
        *,
        tag: str | None = None,
        label: str | None = None,
    ) -> Sandbox: ...

    async def run_command(
        self,
        sandbox_id: str,
        request: CommandRequest,
    ) -> CommandResult: ...

    async def read_file(self, sandbox_id: str, path: str) -> bytes: ...

    async def write_file(
        self,
        sandbox_id: str,
        path: str,
        content: str | bytes,
    ) -> str: ...

    async def list_files(self, sandbox_id: str, path: str = "/") -> list[FileEntry]: ...

    async def checkpoint(self, sandbox_id: str, label: str | None = None) -> Checkpoint: ...

    async def rollback(self, sandbox_id: str, checkpoint_id: str) -> RollbackResult: ...

    async def destroy(self, sandbox_id: str) -> bool: ...

    async def health(self) -> ProviderHealthReport: ...

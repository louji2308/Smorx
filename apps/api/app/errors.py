from __future__ import annotations

from enum import StrEnum


class FailureCategory(StrEnum):
    """Explicit infrastructure failure categories (Phase 1 taxonomy)."""

    CONFIGURATION = "configuration_failure"
    AUTHENTICATION = "authentication_failure"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MODEL_UNAVAILABLE = "model_unavailable"
    REQUEST_TIMEOUT = "request_timeout"
    RATE_LIMIT = "rate_limit"
    SANDBOX_CREATION = "sandbox_creation_failure"
    SANDBOX_EXECUTION = "sandbox_execution_failure"
    COMMAND_TIMEOUT = "command_timeout"
    CLEANUP = "cleanup_failure"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    UNKNOWN = "unknown"


class FailureCode(StrEnum):
    """Plan-aligned failure codes (F1-F10) for cross-phase consistency."""

    F1_BUILD = "F1"
    F2_UNIT_TEST = "F2"
    F3_INTEGRATION = "F3"
    F4_ENVIRONMENT = "F4"
    F5_TIMEOUT = "F5"
    F6_PERMISSION = "F6"
    F7_TOOL = "F7"
    F8_AMBIGUOUS = "F8"
    F9_ACCEPTANCE = "F9"
    F10_POLICY = "F10"


Detail = dict[str, object]


class InfrastructureError(Exception):
    """Base error for every infrastructure failure.

    Carries a machine-readable category, code, correlation identifiers and
    optional detail for structured diagnosis. Never contains secrets.
    """

    def __init__(
        self,
        category: FailureCategory,
        message: str,
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.code = code
        self.request_id = request_id
        self.run_id = run_id
        self.operation_id = operation_id
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.detail = detail or {}

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category.value,
            "code": self.code.value if self.code else None,
            "message": self.message,
            "request_id": self.request_id,
            "run_id": self.run_id,
            "operation_id": self.operation_id,
            "provider": self.provider,
            "model": self.model,
            "status_code": self.status_code,
            "detail": self.detail,
        }

    def __str__(self) -> str:
        return f"[{self.category.value}]" f"{f'/{self.code.value}' if self.code else ''} {self.message}"


class ConfigurationError(InfrastructureError):
    """Invalid/missing configuration."""

    def __init__(
        self,
        message: str = "Invalid infrastructure configuration",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.CONFIGURATION,
            message,
            code=code,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


class AuthenticationError(InfrastructureError):
    """Credential rejection by a provider."""

    def __init__(
        self,
        message: str = "Authentication with provider failed",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.AUTHENTICATION,
            message,
            code=code,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


class ProviderUnavailableError(InfrastructureError):
    """Provider endpoint cannot serve requests."""

    def __init__(
        self,
        message: str = "Provider is unavailable",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.PROVIDER_UNAVAILABLE,
            message,
            code=code,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


class ModelUnavailableError(InfrastructureError):
    """Requested model is not present/selectable."""

    def __init__(
        self,
        message: str = "Requested model is unavailable",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.MODEL_UNAVAILABLE,
            message,
            code=code,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


class RequestTimeoutError(InfrastructureError):
    """Provider/model request exceeded its timeout budget."""

    def __init__(
        self,
        message: str = "Provider request timed out",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.REQUEST_TIMEOUT,
            message,
            code=code or FailureCode.F5_TIMEOUT,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


class RateLimitError(InfrastructureError):
    """Provider rate limit reached."""

    def __init__(
        self,
        message: str = "Provider rate limit reached",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.RATE_LIMIT,
            message,
            code=code,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


class SandboxCreationError(InfrastructureError):
    """Sandbox could not be created/instantiated."""

    def __init__(
        self,
        message: str = "Sandbox creation failed",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.SANDBOX_CREATION,
            message,
            code=code,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


class SandboxExecutionError(InfrastructureError):
    """Sandbox command execution failed at the infrastructure level."""

    def __init__(
        self,
        message: str = "Sandbox command execution failed",
        *,
        exit_code: int | None = None,
        stderr: str | None = None,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        failure_detail: Detail = dict(detail or {})
        if exit_code is not None:
            failure_detail["exit_code"] = exit_code
        if stderr:
            failure_detail["stderr"] = stderr
        super().__init__(
            FailureCategory.SANDBOX_EXECUTION,
            message,
            code=code,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=failure_detail,
        )

    def to_dict(self) -> dict[str, object]:
        return super().to_dict()


class CommandTimeoutError(InfrastructureError):
    """A sandbox command exceeded its timeout budget."""

    def __init__(
        self,
        message: str = "Sandbox command timed out",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.COMMAND_TIMEOUT,
            message,
            code=code or FailureCode.F5_TIMEOUT,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


class CleanupError(InfrastructureError):
    """Sandbox resource cleanup failed."""

    def __init__(
        self,
        message: str = "Sandbox cleanup failed",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.CLEANUP,
            message,
            code=code,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


class UnsupportedCapabilityError(InfrastructureError):
    """A capability is explicitly unsupported by the current provider adapter."""

    def __init__(
        self,
        message: str = "Capability is not supported by this provider",
        *,
        code: FailureCode | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        operation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        detail: Detail | None = None,
    ) -> None:
        super().__init__(
            FailureCategory.UNSUPPORTED_CAPABILITY,
            message,
            code=code,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )


def classify_http_status(
    status_code: int,
    *,
    message: str = "Provider returned an error status",
    request_id: str | None = None,
    run_id: str | None = None,
    operation_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    detail: Detail | None = None,
) -> InfrastructureError:
    """Map an HTTP status from a provider onto the failure taxonomy."""
    if status_code in (401, 403):
        return AuthenticationError(
            message=message,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )
    if status_code == 404:
        return ModelUnavailableError(
            message=message,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )
    if status_code == 429:
        return RateLimitError(
            message=message,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )
    if status_code in (500, 502, 503, 504):
        return ProviderUnavailableError(
            message=message,
            request_id=request_id,
            run_id=run_id,
            operation_id=operation_id,
            provider=provider,
            model=model,
            status_code=status_code,
            detail=detail,
        )
    return InfrastructureError(
        FailureCategory.UNKNOWN,
        message,
        request_id=request_id,
        run_id=run_id,
        operation_id=operation_id,
        provider=provider,
        model=model,
        status_code=status_code,
        detail=detail,
    )

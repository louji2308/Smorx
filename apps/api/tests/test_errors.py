from __future__ import annotations

from collections.abc import Callable

import pytest

from app.errors import (
    AuthenticationError,
    CleanupError,
    CommandTimeoutError,
    ConfigurationError,
    FailureCategory,
    FailureCode,
    InfrastructureError,
    ModelUnavailableError,
    ProviderUnavailableError,
    RateLimitError,
    RequestTimeoutError,
    SandboxCreationError,
    SandboxExecutionError,
    UnsupportedCapabilityError,
    classify_http_status,
)

_ERROR_CASES: list[tuple[Callable[[str], InfrastructureError], FailureCategory]] = [
    (ConfigurationError, FailureCategory.CONFIGURATION),
    (AuthenticationError, FailureCategory.AUTHENTICATION),
    (ProviderUnavailableError, FailureCategory.PROVIDER_UNAVAILABLE),
    (ModelUnavailableError, FailureCategory.MODEL_UNAVAILABLE),
    (RequestTimeoutError, FailureCategory.REQUEST_TIMEOUT),
    (RateLimitError, FailureCategory.RATE_LIMIT),
    (SandboxCreationError, FailureCategory.SANDBOX_CREATION),
    (SandboxExecutionError, FailureCategory.SANDBOX_EXECUTION),
    (CommandTimeoutError, FailureCategory.COMMAND_TIMEOUT),
    (CleanupError, FailureCategory.CLEANUP),
    (UnsupportedCapabilityError, FailureCategory.UNSUPPORTED_CAPABILITY),
]


@pytest.mark.parametrize(("exc_type", "category"), _ERROR_CASES)
def test_error_subclass_categories(
    exc_type: Callable[[str], InfrastructureError], category: FailureCategory
) -> None:
    err = exc_type("boom")
    assert err.category is category
    assert err.category.value == category.value
    assert str(err).startswith(f"[{category.value}]")


def test_to_dict_structure() -> None:
    err = SandboxExecutionError(
        "sandbox command failed",
        exit_code=1,
        stderr="segfault",
        code=FailureCode.F7_TOOL,
        request_id="req-1",
        run_id="run-1",
        operation_id="op-1",
        provider="nebius_contree",
        model="m1",
        status_code=200,
        detail={"extra": "value"},
    )
    data = err.to_dict()
    assert set(data) == {
        "category",
        "code",
        "message",
        "request_id",
        "run_id",
        "operation_id",
        "provider",
        "model",
        "status_code",
        "detail",
    }
    assert data["category"] == "sandbox_execution_failure"
    assert data["code"] == "F7"
    assert data["message"] == "sandbox command failed"
    assert data["request_id"] == "req-1"
    assert data["run_id"] == "run-1"
    assert data["operation_id"] == "op-1"
    assert data["provider"] == "nebius_contree"
    assert data["model"] == "m1"
    assert data["status_code"] == 200
    assert data["detail"] == {"extra": "value", "exit_code": 1, "stderr": "segfault"}


def test_sandbox_execution_error_carries_exit_code_and_stderr() -> None:
    err = SandboxExecutionError("run failed", exit_code=2, stderr="traceback")
    assert err.detail["exit_code"] == 2
    assert err.detail["stderr"] == "traceback"
    assert "run failed" in str(err)


def test_sandbox_execution_error_detail_empty_without_values() -> None:
    err = SandboxExecutionError("run failed")
    assert err.detail == {}


def test_timeout_errors_default_to_code_f5() -> None:
    assert RequestTimeoutError().code is FailureCode.F5_TIMEOUT
    assert CommandTimeoutError().code is FailureCode.F5_TIMEOUT


def test_request_timeout_allows_explicit_code() -> None:
    err = RequestTimeoutError(code=FailureCode.F4_ENVIRONMENT)
    assert err.code is FailureCode.F4_ENVIRONMENT


def test_other_errors_have_no_default_code() -> None:
    assert AuthenticationError().code is None
    assert ConfigurationError().code is None
    assert RateLimitError().code is None


@pytest.mark.parametrize(
    ("status", "expected_type", "category"),
    [
        (401, AuthenticationError, FailureCategory.AUTHENTICATION),
        (403, AuthenticationError, FailureCategory.AUTHENTICATION),
        (404, ModelUnavailableError, FailureCategory.MODEL_UNAVAILABLE),
        (429, RateLimitError, FailureCategory.RATE_LIMIT),
        (500, ProviderUnavailableError, FailureCategory.PROVIDER_UNAVAILABLE),
        (502, ProviderUnavailableError, FailureCategory.PROVIDER_UNAVAILABLE),
        (503, ProviderUnavailableError, FailureCategory.PROVIDER_UNAVAILABLE),
        (504, ProviderUnavailableError, FailureCategory.PROVIDER_UNAVAILABLE),
        (400, InfrastructureError, FailureCategory.UNKNOWN),
    ],
)
def test_classify_http_status(
    status: int,
    expected_type: type[InfrastructureError],
    category: FailureCategory,
) -> None:
    err = classify_http_status(status, message="provider said no", provider="nebius_token_factory")
    assert isinstance(err, expected_type)
    assert err.category is category
    assert err.status_code == status
    assert err.message == "provider said no"
    assert err.provider == "nebius_token_factory"


def test_classify_http_status_unknown_status() -> None:
    err = classify_http_status(418)
    assert isinstance(err, InfrastructureError)
    assert not isinstance(err, AuthenticationError)
    assert err.category is FailureCategory.UNKNOWN
    assert err.status_code == 418

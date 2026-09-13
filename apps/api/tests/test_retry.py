from __future__ import annotations

import pytest

from app.errors import AuthenticationError, ConfigurationError, ProviderUnavailableError
from app.providers.token_factory.retry import RetryPolicy


def _policy() -> RetryPolicy:
    return RetryPolicy(max_attempts=3, backoff_factor=1.0, base_delay_seconds=0.001)


async def test_success_on_first_attempt() -> None:
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await _policy().execute(fn)
    assert result == "ok"
    assert calls == 1


async def test_retries_transient_failures_until_success() -> None:
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ProviderUnavailableError("provider down")
        return "recovered"

    result = await _policy().execute(fn)
    assert result == "recovered"
    assert calls == 3


async def test_raises_last_error_after_max_attempts() -> None:
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        raise ProviderUnavailableError("provider down")

    with pytest.raises(ProviderUnavailableError):
        await _policy().execute(fn)
    assert calls == 3


@pytest.mark.parametrize(
    "error",
    [
        AuthenticationError("auth failed"),
        ConfigurationError("bad config"),
    ],
)
async def test_does_not_retry_non_transient_errors(error: Exception) -> None:
    calls = 0

    async def fn() -> None:
        nonlocal calls
        calls += 1
        raise error

    with pytest.raises(type(error)):
        await _policy().execute(fn)
    assert calls == 1


async def test_does_not_catch_non_infrastructure_exceptions() -> None:
    calls = 0

    async def fn() -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("plain failure")

    with pytest.raises(RuntimeError):
        await _policy().execute(fn)
    assert calls == 1


def test_max_attempts_below_one_rejected() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0, backoff_factor=1.0)
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=-2, backoff_factor=1.0)

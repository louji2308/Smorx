from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx2
import openai
import pytest

from app.contracts import ModelRequest
from app.errors import (
    AuthenticationError,
    ConfigurationError,
    FailureCategory,
    ModelUnavailableError,
    ProviderUnavailableError,
    RateLimitError,
    RequestTimeoutError,
)
from app.providers.token_factory import TokenFactoryClient
from app.settings import Settings


def _make_request(model: str = "nvidia/test-model") -> ModelRequest:
    return ModelRequest(
        model=model,
        system="system prompt",
        prompt="user prompt",
        request_id="req-1",
        run_id="run-1",
        timestamp=datetime.now(UTC),
    )


def _make_openai_completion(
    content: str,
    *,
    model: str = "nvidia/test-model",
    usage: SimpleNamespace | None = None,
) -> SimpleNamespace:
    usage_data = usage or SimpleNamespace(
        prompt_tokens=9, completion_tokens=3, total_tokens=12
    )
    message = SimpleNamespace(content=content, role="assistant")
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(
        id="chatcmpl-fake",
        model=model,
        created=int(datetime.now(UTC).timestamp()),
        choices=[choice],
        usage=usage_data,
    )


def _make_openai_status_error(
    error_type: type[openai.APIStatusError], status_code: int
) -> openai.APIStatusError:
    request = httpx2.Request("POST", "https://api.example.com/v1/chat/completions")
    response = httpx2.Response(status_code=status_code, request=request)
    return error_type(f"status {status_code}", response=response, body=None)


def _patch_create(
    client: TokenFactoryClient,
    monkeypatch: pytest.MonkeyPatch,
    fake: object,
) -> None:
    assert client._client is not None, "client must be initialized for patching"
    monkeypatch.setattr(client._client.chat.completions, "create", fake)


async def test_chat_completion_maps_request_to_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        nebius_api_key="sk-test", nebius_inference_base_url="https://api.example.com/v1"
    )
    client = TokenFactoryClient(settings=settings)
    completion = _make_openai_completion("INFRA_OK")

    async def fake_create(*args: object, **kwargs: object) -> object:
        await asyncio.sleep(0.05)
        return completion

    _patch_create(client, monkeypatch, fake_create)
    response = await client.chat_completion(_make_request())

    assert response.provider == "nebius_token_factory"
    assert response.content == "INFRA_OK"
    assert response.model == "nvidia/test-model"
    assert response.id == "chatcmpl-fake"
    assert response.finish_reason == "stop"
    assert response.request_id == "req-1"
    assert response.run_id == "run-1"
    assert response.duration_ms > 0
    assert response.usage.total_tokens == 12
    assert response.usage.prompt_tokens == 9
    assert response.usage.completion_tokens == 3


async def test_chat_completion_accepts_nullable_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(nebius_api_key="sk-test")
    client = TokenFactoryClient(settings=settings)
    completion = _make_openai_completion("ok", usage=None)
    completion.usage = None

    async def fake_create(*args: object, **kwargs: object) -> object:
        return completion

    _patch_create(client, monkeypatch, fake_create)
    response = await client.chat_completion(_make_request())
    assert response.content == "ok"
    assert response.usage.total_tokens == 0


async def test_chat_completion_requires_api_key() -> None:
    client = TokenFactoryClient(settings=Settings(nebius_api_key=""))
    with pytest.raises(ConfigurationError) as exc_info:
        await client.chat_completion(_make_request())
    assert exc_info.value.category is FailureCategory.CONFIGURATION


async def test_chat_completion_retries_transient_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        nebius_api_key="sk-test",
        nebius_inference_base_url="https://api.example.com/v1",
        model_max_retries=3,
        model_retry_backoff_factor=1.0,
    )
    client = TokenFactoryClient(settings=settings)
    completion = _make_openai_completion("INFRA_OK")
    calls = {"count": 0}

    async def flaky_create(*args: object, **kwargs: object) -> object:
        calls["count"] += 1
        if calls["count"] < 3:
            request = httpx2.Request(
                "POST", "https://api.example.com/v1/chat/completions"
            )
            raise openai.InternalServerError(
                "upstream 500", response=httpx2.Response(500, request=request), body=None
            )
        return completion

    _patch_create(client, monkeypatch, flaky_create)
    response = await client.chat_completion(_make_request())
    assert response.content == "INFRA_OK"
    assert calls["count"] == 3


async def test_chat_completion_does_not_retry_auth_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        nebius_api_key="sk-test",
        nebius_inference_base_url="https://api.example.com/v1",
    )
    client = TokenFactoryClient(settings=settings)
    calls = {"count": 0}

    async def auth_failing_create(*args: object, **kwargs: object) -> object:
        calls["count"] += 1
        request = httpx2.Request(
            "POST", "https://api.example.com/v1/chat/completions"
        )
        raise openai.AuthenticationError(
            "denied",
            response=httpx2.Response(401, request=request),
            body=None,
        )

    _patch_create(client, monkeypatch, auth_failing_create)
    with pytest.raises(AuthenticationError):
        await client.chat_completion(_make_request())
    assert calls["count"] == 1


async def test_openai_authentication_error_maps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TokenFactoryClient(settings=Settings(nebius_api_key="sk-test"))
    error = _make_openai_status_error(openai.AuthenticationError, 401)

    async def fake_create(*args: object, **kwargs: object) -> object:
        raise error

    _patch_create(client, monkeypatch, fake_create)
    with pytest.raises(AuthenticationError) as exc_info:
        await client.chat_completion(_make_request())
    assert exc_info.value.status_code == 401
    assert exc_info.value.category is FailureCategory.AUTHENTICATION


async def test_openai_rate_limit_error_maps(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TokenFactoryClient(settings=Settings(nebius_api_key="sk-test"))
    error = _make_openai_status_error(openai.RateLimitError, 429)

    async def fake_create(*args: object, **kwargs: object) -> object:
        raise error

    _patch_create(client, monkeypatch, fake_create)
    with pytest.raises(RateLimitError) as exc_info:
        await client.chat_completion(_make_request())
    assert exc_info.value.status_code == 429
    assert exc_info.value.category is FailureCategory.RATE_LIMIT


async def test_openai_not_found_error_maps_to_model_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TokenFactoryClient(settings=Settings(nebius_api_key="sk-test"))
    error = _make_openai_status_error(openai.NotFoundError, 404)

    async def fake_create(*args: object, **kwargs: object) -> object:
        raise error

    _patch_create(client, monkeypatch, fake_create)
    with pytest.raises(ModelUnavailableError) as exc_info:
        await client.chat_completion(_make_request())
    assert exc_info.value.status_code == 404
    assert exc_info.value.category is FailureCategory.MODEL_UNAVAILABLE


async def test_openai_internal_error_maps_to_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TokenFactoryClient(settings=Settings(nebius_api_key="sk-test"))
    error = _make_openai_status_error(openai.InternalServerError, 500)

    async def fake_create(*args: object, **kwargs: object) -> object:
        raise error

    _patch_create(client, monkeypatch, fake_create)
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await client.chat_completion(_make_request())
    assert exc_info.value.status_code == 500
    assert exc_info.value.category is FailureCategory.PROVIDER_UNAVAILABLE


async def test_openai_timeout_error_maps(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TokenFactoryClient(settings=Settings(nebius_api_key="sk-test"))
    request = httpx2.Request("POST", "https://api.example.com/v1/chat/completions")
    error = openai.APITimeoutError(request)

    async def fake_create(*args: object, **kwargs: object) -> object:
        raise error

    _patch_create(client, monkeypatch, fake_create)
    with pytest.raises(RequestTimeoutError) as exc_info:
        await client.chat_completion(_make_request())
    assert exc_info.value.category is FailureCategory.REQUEST_TIMEOUT

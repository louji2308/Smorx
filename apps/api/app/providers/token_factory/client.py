from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, NoReturn, cast

import openai
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    completion_create_params,
)
from openai.types.chat.chat_completion import ChatCompletion

from ...contracts import (
    HealthStatus,
    ModelRequest,
    ModelResponse,
    ProviderHealthReport,
    TokenUsage,
)
from ...errors import (
    AuthenticationError,
    ConfigurationError,
    FailureCategory,
    InfrastructureError,
    ModelUnavailableError,
    ProviderUnavailableError,
    RateLimitError,
    RequestTimeoutError,
    classify_http_status,
)
from ...observability import redact_secrets
from ...settings import Settings, get_settings
from .retry import RetryPolicy

PROVIDER = "nebius_token_factory"


def _raise_translated(
    exc: openai.OpenAIError,
    *,
    model: str | None = None,
    request_id: str | None = None,
    run_id: str | None = None,
) -> NoReturn:
    """Map an openai SDK error onto the infrastructure failure taxonomy."""
    if isinstance(exc, openai.APITimeoutError):
        raise RequestTimeoutError(
            f"Token Factory request timed out: {redact_secrets(str(exc))}",
            provider=PROVIDER,
            model=model,
            request_id=request_id,
            run_id=run_id,
        ) from exc
    if isinstance(exc, openai.APIConnectionError):
        raise ProviderUnavailableError(
            f"Token Factory connection failed: {redact_secrets(str(exc))}",
            provider=PROVIDER,
            model=model,
            request_id=request_id,
            run_id=run_id,
        ) from exc
    if isinstance(exc, openai.AuthenticationError):
        raise AuthenticationError(
            f"Token Factory authentication failed: {redact_secrets(str(exc))}",
            provider=PROVIDER,
            model=model,
            request_id=request_id,
            run_id=run_id,
            status_code=exc.status_code,
        ) from exc
    if isinstance(exc, openai.RateLimitError):
        raise RateLimitError(
            f"Token Factory rate limit exceeded: {redact_secrets(str(exc))}",
            provider=PROVIDER,
            model=model,
            request_id=request_id,
            run_id=run_id,
            status_code=exc.status_code,
        ) from exc
    if isinstance(exc, openai.NotFoundError):
        raise ModelUnavailableError(
            f"Token Factory model not found: {redact_secrets(str(exc))}",
            provider=PROVIDER,
            model=model,
            request_id=request_id,
            run_id=run_id,
            status_code=exc.status_code,
        ) from exc
    if isinstance(exc, openai.InternalServerError):
        raise ProviderUnavailableError(
            f"Token Factory server error: {redact_secrets(str(exc))}",
            provider=PROVIDER,
            model=model,
            request_id=request_id,
            run_id=run_id,
            status_code=exc.status_code,
        ) from exc
    if isinstance(exc, openai.APIStatusError):
        raise classify_http_status(
            exc.status_code,
            provider=PROVIDER,
            model=model,
            request_id=request_id,
            run_id=run_id,
            detail={"provider_message": redact_secrets(str(exc))},
        ) from exc
    raise InfrastructureError(
        FailureCategory.UNKNOWN,
        f"Token Factory provider error: {redact_secrets(str(exc))}",
        provider=PROVIDER,
        model=model,
        request_id=request_id,
        run_id=run_id,
    ) from exc


class TokenFactoryClient:
    """Nebius Token Factory OpenAI-compatible inference provider adapter."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings if settings is not None else get_settings()
        self._client: AsyncOpenAI | None = None
        if self._settings.nebius_api_key:
            self._client = AsyncOpenAI(
                base_url=self._settings.nebius_inference_base_url,
                api_key=self._settings.nebius_api_key,
                timeout=self._settings.model_timeout_seconds,
                max_retries=0,
            )
        self._retry_policy = RetryPolicy(
            max_attempts=self._settings.model_max_retries,
            backoff_factor=self._settings.model_retry_backoff_factor,
        )

    def _require_client(self) -> AsyncOpenAI:
        if self._client is None:
            raise ConfigurationError(
                "NEBIUS_API_KEY is required to use the Nebius Token Factory inference provider"
            )
        return self._client

    async def chat_completion(self, request: ModelRequest) -> ModelResponse:
        """Send a chat completion request and translate the result."""
        client = self._require_client()
        messages: list[ChatCompletionMessageParam] = []
        if request.system:
            messages.append(
                ChatCompletionSystemMessageParam(content=request.system, role="system")
            )
        messages.append(
            ChatCompletionUserMessageParam(content=request.prompt, role="user")
        )

        params: dict[str, Any] = {"model": request.model, "messages": messages}
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.max_tokens is not None:
            params["max_tokens"] = request.max_tokens
        if request.response_format is not None:
            params["response_format"] = cast(
                completion_create_params.ResponseFormat, request.response_format
            )

        started = time.monotonic()
        completion = await self._retry_policy.execute(
            lambda: self._create_once(client, params, request)
        )
        duration_ms = int((time.monotonic() - started) * 1000)

        if not completion.choices:
            raise InfrastructureError(
                FailureCategory.UNKNOWN,
                "Token Factory returned a completion without choices",
                provider=PROVIDER,
                model=request.model,
                request_id=request.request_id,
                run_id=request.run_id,
            )
        return self._to_model_response(
            completion, request, duration_ms=duration_ms
        )

    async def list_models(self) -> list[str]:
        """List model id strings available on the provider."""
        client = self._require_client()
        try:
            return [model.id async for model in client.models.list()]
        except openai.OpenAIError as exc:
            _raise_translated(exc)

    async def _create_once(
        self,
        client: AsyncOpenAI,
        params: dict[str, Any],
        request: ModelRequest,
    ) -> Any:
        """Issue a single chat completion attempt, translating errors as raised.

        Structured exceptions carry the request tokens using the task-scope
        ids from the request so failures remain attributable to the run.
        """
        try:
            return await client.chat.completions.create(**params)
        except openai.OpenAIError as exc:
            _raise_translated(
                exc,
                model=request.model,
                request_id=request.request_id,
                run_id=request.run_id,
            )

    async def health(self, model: str | None = None) -> ProviderHealthReport:
        """Report provider health by listing models and verifying the model."""
        started = time.monotonic()
        checked_at = datetime.now(UTC)
        target_model = model or self._settings.nemotron_model_nano
        try:
            models = await self.list_models()
        except ConfigurationError:
            raise
        except InfrastructureError as exc:
            return ProviderHealthReport(
                provider=PROVIDER,
                status=HealthStatus.UNHEALTHY,
                latency_ms=int((time.monotonic() - started) * 1000),
                checked_at=checked_at,
                detail=str(exc),
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        if target_model in models:
            return ProviderHealthReport(
                provider=PROVIDER,
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
                checked_at=checked_at,
                models_verified=models,
            )
        return ProviderHealthReport(
            provider=PROVIDER,
            status=HealthStatus.DEGRADED,
            latency_ms=latency_ms,
            checked_at=checked_at,
            detail=(
                f"Requested model {target_model!r} not found among "
                f"{len(models)} available models"
            ),
            models_verified=models,
        )

    @staticmethod
    def _to_model_response(
        completion: ChatCompletion,
        request: ModelRequest,
        *,
        duration_ms: int,
    ) -> ModelResponse:
        choice = completion.choices[0]
        usage_data = completion.usage
        usage = (
            TokenUsage(
                prompt_tokens=usage_data.prompt_tokens,
                completion_tokens=usage_data.completion_tokens,
                total_tokens=usage_data.total_tokens,
            )
            if usage_data is not None
            else TokenUsage()
        )
        return ModelResponse(
            id=completion.id,
            model=completion.model,
            provider=PROVIDER,
            content=choice.message.content or "",
            finish_reason=choice.finish_reason,
            usage=usage,
            duration_ms=duration_ms,
            created_at=datetime.fromtimestamp(completion.created, tz=UTC),
            request_id=request.request_id,
            run_id=request.run_id,
        )

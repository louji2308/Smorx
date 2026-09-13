from __future__ import annotations

import pytest

from app.contracts import HealthStatus, ModelTier, RoutingCapability
from app.errors import ConfigurationError
from app.model.nemotron import NemotronModelService
from app.model.router import ModelRouter
from app.settings import Settings
from tests.conftest import FakeTokenFactoryClient, make_model_request


def _settings() -> Settings:
    return Settings(
        nebius_api_key="k",
        nebius_ai_project="p",
        nemotron_model_nano="model-nano",
        nemotron_model_super="model-super",
        nemotron_model_ultra="model-ultra",
    )


def _service(client: FakeTokenFactoryClient) -> NemotronModelService:
    settings = _settings()
    return NemotronModelService(
        client=client, router=ModelRouter(settings=settings), settings=settings
    )


async def test_complete_routes_capability_and_binds_response() -> None:
    client = FakeTokenFactoryClient(content="OK", model="model-super")
    completion = await _service(client).complete(make_model_request(model="coding"))
    assert completion.response.content == "OK"
    assert completion.response.request_id == "req-1"
    assert completion.response.run_id == "run-1"
    assert completion.response.model == "model-super"
    assert completion.routing.capability is RoutingCapability.CODING
    assert completion.routing.selected_model == "model-super"
    assert completion.routing.run_id == "run-1"
    assert client.last_request is not None
    assert client.last_request.model == "model-super"


async def test_complete_routes_explicit_model_id() -> None:
    client = FakeTokenFactoryClient(content="OK", model="model-ultra")
    completion = await _service(client).complete(
        make_model_request(model="model-ultra")
    )
    assert completion.routing.tier is ModelTier.ULTRA
    assert completion.routing.selected_model == "model-ultra"
    assert completion.response.model == "model-ultra"


async def test_complete_routes_explicit_tier_name() -> None:
    client = FakeTokenFactoryClient(content="OK", model="model-nano")
    completion = await _service(client).complete(make_model_request(model="nano"))
    assert completion.routing.tier is ModelTier.NANO
    assert completion.response.model == "model-nano"


async def test_complete_rejects_empty_model() -> None:
    service = _service(FakeTokenFactoryClient(content="OK"))
    with pytest.raises(ConfigurationError) as exc_info:
        await service.complete(make_model_request(model="   "))
    assert exc_info.value.request_id == "req-1"


async def test_complete_rejects_unknown_model() -> None:
    service = _service(FakeTokenFactoryClient(content="OK"))
    with pytest.raises(ConfigurationError):
        await service.complete(make_model_request(model="not-a-real-model"))


async def test_health_delegates_to_client() -> None:
    client = FakeTokenFactoryClient(content="OK")
    report = await _service(client).health()
    assert report is client.health_report
    assert report.provider == "nebius_token_factory"
    assert report.status is HealthStatus.HEALTHY

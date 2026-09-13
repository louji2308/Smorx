from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, cast

from app.contracts import SandboxExecutionPort
from app.errors import ConfigurationError
from app.model import ModelRouter, NemotronModelService
from app.runtime.proof import ProofPathService
from app.runtime.service import AgentRuntime
from app.settings import Settings, get_settings


@dataclass
class Dependencies:
    settings: Settings
    model_client: Any
    model_router: ModelRouter
    model_service: NemotronModelService
    sandbox: SandboxExecutionPort | None
    runtime: AgentRuntime
    proof: ProofPathService


def build_model_client(settings: Settings) -> Any:
    from app.providers.token_factory import TokenFactoryClient

    return TokenFactoryClient(settings=settings)


def build_model_service(settings: Settings) -> NemotronModelService:
    client = build_model_client(settings)
    router = ModelRouter(settings=settings)
    return NemotronModelService(client=client, router=router, settings=settings)


def build_sandbox(settings: Settings) -> SandboxExecutionPort:
    try:
        module: Any = importlib.import_module("app.providers.sandbox")
    except ImportError as exc:
        raise ConfigurationError(
            "ContreeSandboxAdapter is unavailable: app.providers.sandbox is not installed"
        ) from exc
    return cast(SandboxExecutionPort, module.ContreeSandboxAdapter(settings=settings))


def _build_sandbox_optional(settings: Settings) -> SandboxExecutionPort | None:
    try:
        return build_sandbox(settings)
    except ConfigurationError:
        return None


def build_dependencies(settings: Settings | None = None) -> Dependencies:
    resolved = settings if settings is not None else get_settings()
    model_client = build_model_client(resolved)
    model_router = ModelRouter(settings=resolved)
    model_service = NemotronModelService(
        client=model_client, router=model_router, settings=resolved
    )
    sandbox = _build_sandbox_optional(resolved)
    runtime = AgentRuntime(settings=resolved, model_service=model_service, sandbox=sandbox)
    proof = ProofPathService(settings=resolved, model_service=model_service, sandbox=sandbox)
    return Dependencies(
        settings=resolved,
        model_client=model_client,
        model_router=model_router,
        model_service=model_service,
        sandbox=sandbox,
        runtime=runtime,
        proof=proof,
    )

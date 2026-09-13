from __future__ import annotations

import logging
from typing import Any, Protocol

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.errors import ConfigurationError, InfrastructureError
from app.observability import redact_secrets
from app.runtime.proof import ProofPathService
from app.runtime.service import AgentRuntime
from app.settings import Settings

_LOGGER = logging.getLogger("smorx.api")

_REMEDIATION = "Set NEBIUS_API_KEY and NEBIUS_AI_PROJECT/NEBIUS_PROJECT_ID in .env"


def redact_exc_detail(detail: dict[str, Any]) -> dict[str, Any]:
    return {k: redact_secrets(str(v)) if isinstance(v, str) else v for k, v in detail.items()}


class RoutesDependencies(Protocol):
    settings: Settings
    runtime: AgentRuntime
    proof: ProofPathService


def create_router(deps: RoutesDependencies) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    def root() -> dict[str, str]:
        return {"name": "Smorx API", "phase": "1-infrastructure", "version": "0.1.0"}

    @router.get("/health")
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/api/v1/infra/status")
    async def infra_status() -> dict[str, Any]:
        return await deps.runtime.health()

    @router.post("/api/v1/infra/proof")
    async def infra_proof() -> JSONResponse:
        try:
            result = await deps.proof.execute()
        except ConfigurationError as exc:
            return JSONResponse(
                status_code=503,
                content={
                    "category": exc.category.value,
                    "message": redact_secrets(exc.message),
                    "detail": redact_exc_detail(exc.detail),
                    "remediation": _REMEDIATION,
                },
            )
        except InfrastructureError as exc:
            body = exc.to_dict()
            body["detail"] = redact_exc_detail(exc.detail)
            return JSONResponse(status_code=502, content=body)
        except Exception as exc:
            _LOGGER.warning(
                "proof endpoint failure: %s",
                redact_secrets(f"{type(exc).__name__}: {exc}"),
            )
            return JSONResponse(
                status_code=500,
                content={"category": "unknown", "message": "internal error"},
            )
        return JSONResponse(status_code=200, content=result.model_dump(mode="json"))

    return router

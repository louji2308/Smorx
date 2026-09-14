"""Phase 6 (Discover + Govern) behavior HTTP surface.

This module is a thin transport layer: every endpoint delegates to an injected
``BehaviorAdapter`` and performs no persistence or query logic itself. It mirrors
the infra router conventions from ``app.api.routes`` (per-handler ``try/except``
with ``redact_secrets`` logging and a normalized 500 JSON body).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.behavior import BehaviorAdapter
from app.behavior.contract import (
    ActivateResult,
    BehaviorContext,
    ConstitutionView,
    FindingsSet,
    GraphDto,
    ReadinessView,
)
from app.observability import redact_secrets

_LOGGER = logging.getLogger("smorx.api.behavior")


def create_behavior_router(behavior: BehaviorAdapter) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/behavior/context", response_model=BehaviorContext)
    def behavior_context() -> BehaviorContext | JSONResponse:
        try:
            return behavior.context()
        except Exception as exc:
            _LOGGER.warning(
                "behavior context endpoint failure: %s",
                redact_secrets(f"{type(exc).__name__}: {exc}"),
            )
            return JSONResponse(
                status_code=500,
                content={"category": "behavior", "message": "internal error"},
            )

    @router.get("/api/v1/behavior/findings", response_model=FindingsSet)
    def behavior_findings() -> FindingsSet | JSONResponse:
        try:
            return behavior.findings()
        except Exception as exc:
            _LOGGER.warning(
                "behavior findings endpoint failure: %s",
                redact_secrets(f"{type(exc).__name__}: {exc}"),
            )
            return JSONResponse(
                status_code=500,
                content={"category": "behavior", "message": "internal error"},
            )

    @router.get("/api/v1/behavior/graph", response_model=GraphDto)
    def behavior_graph() -> GraphDto | JSONResponse:
        try:
            return behavior.graph()
        except Exception as exc:
            _LOGGER.warning(
                "behavior graph endpoint failure: %s",
                redact_secrets(f"{type(exc).__name__}: {exc}"),
            )
            return JSONResponse(
                status_code=500,
                content={"category": "behavior", "message": "internal error"},
            )

    @router.get("/api/v1/behavior/constitution", response_model=ConstitutionView)
    def behavior_constitution() -> ConstitutionView | JSONResponse:
        try:
            return behavior.constitution()
        except Exception as exc:
            _LOGGER.warning(
                "behavior constitution endpoint failure: %s",
                redact_secrets(f"{type(exc).__name__}: {exc}"),
            )
            return JSONResponse(
                status_code=500,
                content={"category": "behavior", "message": "internal error"},
            )

    @router.get("/api/v1/behavior/readiness", response_model=ReadinessView)
    def behavior_readiness() -> ReadinessView | JSONResponse:
        try:
            return behavior.readiness()
        except Exception as exc:
            _LOGGER.warning(
                "behavior readiness endpoint failure: %s",
                redact_secrets(f"{type(exc).__name__}: {exc}"),
            )
            return JSONResponse(
                status_code=500,
                content={"category": "behavior", "message": "internal error"},
            )

    @router.post("/api/v1/behavior/constitution/activate", response_model=ActivateResult)
    def behavior_activate() -> ActivateResult | JSONResponse:
        try:
            return behavior.activate()
        except Exception as exc:
            _LOGGER.warning(
                "behavior activate endpoint failure: %s",
                redact_secrets(f"{type(exc).__name__}: {exc}"),
            )
            return JSONResponse(
                status_code=500,
                content={"category": "behavior", "message": "internal error"},
            )

    return router

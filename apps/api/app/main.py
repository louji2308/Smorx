from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import create_router
from app.deps import build_dependencies
from app.errors import InfrastructureError
from app.observability import configure_logging
from app.settings import Settings, get_settings


async def _infrastructure_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, InfrastructureError):
        return JSONResponse(
            status_code=500,
            content={"category": "unknown", "message": "internal error"},
        )
    status = exc.status_code or 502
    return JSONResponse(status_code=status, content=exc.to_dict())


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings if settings is not None else get_settings()
    configure_logging(resolved.log_level)
    deps = build_dependencies(resolved)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if resolved.infra_check_on_startup:
            await deps.runtime.health()
        yield

    docs_visible = resolved.app_env != "production"
    app = FastAPI(
        title="Smorx API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_visible else None,
        redoc_url="/redoc" if docs_visible else None,
        openapi_url="/openapi.json" if docs_visible else None,
    )
    app.state.deps = deps
    app.include_router(create_router(deps))
    app.add_exception_handler(InfrastructureError, _infrastructure_error_handler)
    return app


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:create_app", factory=True, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()

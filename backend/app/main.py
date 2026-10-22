"""FastAPI application factory and entrypoint."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.deps import require_api_key
from app.api.routes import evidence, health, incidents, investigations, remediations
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger, set_request_id

logger = get_logger(__name__)

DESCRIPTION = """
IncidentIQ backend API.

Owns the incident lifecycle, evidence collection, LLM-assisted root-cause
analysis and the human approval workflow for simulated remediations.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging on startup."""
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    logger.info(
        "application_started",
        extra={
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "llm_configured": settings.llm_configured,
        },
    )
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description=DESCRIPTION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        """Attach a request id, log the call and expose the request id."""
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        set_request_id(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """Return the canonical error body for application errors."""
        request_id = _request_id()
        logger.warning(
            "application_error",
            extra={"code": exc.code, "status_code": exc.status_code, "path": request.url.path},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_payload(request_id),
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return the canonical error body for request validation failures."""
        request_id = _request_id()
        details = {"errors": _safe_errors(exc.errors())}
        payload = AppError(
            "The request payload is invalid",
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        ).to_payload(request_id)
        return JSONResponse(
            status_code=422, content=payload, headers={"X-Request-ID": request_id}
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Return the canonical error body for HTTP errors."""
        request_id = _request_id()
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        payload = AppError(
            str(exc.detail),
            code=code,
            status_code=exc.status_code,
        ).to_payload(request_id)
        return JSONResponse(
            status_code=exc.status_code, content=payload, headers={"X-Request-ID": request_id}
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Return the canonical error body for unexpected failures."""
        request_id = _request_id()
        logger.exception("unhandled_exception", extra={"path": request.url.path})
        payload = AppError(
            "An unexpected server error occurred",
            code="INTERNAL_ERROR",
            status_code=500,
        ).to_payload(request_id)
        return JSONResponse(
            status_code=500, content=payload, headers={"X-Request-ID": request_id}
        )

    app.include_router(health.router)
    app.include_router(
        health.router, prefix=settings.API_PREFIX, dependencies=[Depends(require_api_key)]
    )

    for router in (
        incidents.router,
        evidence.router,
        investigations.router,
        remediations.router,
    ):
        app.include_router(
            router, prefix=settings.API_PREFIX, dependencies=[Depends(require_api_key)]
        )

    return app


def _request_id() -> str:
    """Return the request id of the current context."""
    from app.core.logging import get_request_id

    return get_request_id() or f"req_{uuid.uuid4().hex[:12]}"


def _safe_errors(errors: list[dict]) -> list[dict]:
    """Return validation errors that are safe to serialise."""
    safe: list[dict] = []
    for error in errors:
        safe.append(
            {
                "loc": [str(part) for part in error.get("loc", [])],
                "msg": str(error.get("msg", "")),
                "type": str(error.get("type", "")),
            }
        )
    return safe


app = create_app()

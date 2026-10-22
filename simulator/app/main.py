from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uuid

from app.core.config import settings
from app.core.logging import logger
from app.api.health import router as health_router
from app.api.scenarios import router as scenarios_router
from app.api.evidence import router as evidence_router
from app.api.payments import router as payments_router
from app.api.remediations import router as remediations_router


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Simulator started successfully on {settings.SIMULATOR_HOST}:{settings.SIMULATOR_PORT} [{settings.SIMULATOR_ENV}]"
    )
    yield
    logger.info("Simulator shutting down")


def create_app() -> FastAPI:
    """Application factory for the IncidentIQ Payment API Simulator."""
    app = FastAPI(
        title="IncidentIQ Payment Service Simulator",
        description="Simulates realistic, reproducible production incidents and telemetry for IncidentIQ RCA platform.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Standard error format conforming to API contract section 9
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        if isinstance(exc.detail, dict):
            error_data = {
                "code": exc.detail.get("code", f"HTTP_{exc.status_code}"),
                "message": exc.detail.get("message", "An error occurred"),
                "request_id": req_id
            }
            if "details" in exc.detail:
                error_data["details"] = exc.detail["details"]
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": error_data}
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "request_id": req_id
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters",
                    "request_id": req_id,
                    "details": exc.errors()
                }
            }
        )

    # Mount API routers
    app.include_router(health_router)
    app.include_router(scenarios_router)
    app.include_router(evidence_router)
    app.include_router(payments_router)
    app.include_router(remediations_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.SIMULATOR_HOST,
        port=settings.SIMULATOR_PORT,
        reload=True
    )

"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_simulator_client, settings_dependency
from app.core.config import Settings
from app.db.session import get_db
from app.services.simulator_client import SimulatorClient

router = APIRouter(tags=["health"])


@router.get("/health", summary="Service health")
def health(
    session: Session = Depends(get_db),
    settings: Settings = Depends(settings_dependency),
    simulator_client: SimulatorClient = Depends(get_simulator_client),
) -> dict:
    """Return the health of the backend and its dependencies."""
    database_status = "ok"
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        database_status = "degraded"

    simulator_status = "unknown"
    try:
        simulator_status = simulator_client.health_status(timeout=2.0)
    except Exception:
        simulator_status = "unreachable"

    status = "ok" if database_status == "ok" and simulator_status != "unreachable" else "degraded"

    return {
        "status": status,
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "database": database_status,
        "simulator": simulator_status,
        "llm": {
            "provider": "gemini",
            "model": settings.GEMINI_MODEL,
            "configured": settings.llm_configured,
        },
    }

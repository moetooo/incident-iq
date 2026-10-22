from fastapi import APIRouter
from typing import Dict, Any

from app.services.state_service import simulator_state_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=Dict[str, Any])
def get_health() -> Dict[str, Any]:
    """Returns simulator health status in accordance with API contract."""
    return simulator_state_service.get_health_status()

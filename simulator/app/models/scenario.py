from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ScenarioId(str, Enum):
    NORMAL = "normal"
    PAYMENT_TIMEOUT = "payment_timeout"
    DATABASE_FAILURE = "database_failure"
    BAD_DEPLOYMENT = "bad_deployment"


class ScenarioStatus(BaseModel):
    scenario_id: ScenarioId
    title: str
    description: str
    is_healthy: bool
    status: str
    activated_at: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ScenarioTriggerResponse(BaseModel):
    status: str = "ok"
    scenario_id: ScenarioId
    message: str
    activated_at: str
    evidence_count_generated: int
    health_status: str


class ResetResponse(BaseModel):
    status: str = "ok"
    scenario: ScenarioId = ScenarioId.NORMAL
    message: str = "Simulator reset to healthy state"
    reset_at: str

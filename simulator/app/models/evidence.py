from enum import Enum
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    LOG = "log"
    METRIC = "metric"
    DEPLOYMENT = "deployment"
    STATE = "state"


class EvidenceItem(BaseModel):
    id: str = Field(description="Stable evidence ID for backend referencing")
    type: str = Field(description="Type: log, metric, deployment, or state")
    source: str = Field(default="payment-api", description="Service generating the evidence")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")
    summary: str = Field(description="Human readable summary of the evidence")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured details")


class EvidenceListResponse(BaseModel):
    items: List[EvidenceItem]
    total: int

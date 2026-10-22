from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class RemediationExecutionRequest(BaseModel):
    """Request model for executing an allowlisted simulated remediation action."""
    action: str = Field(..., min_length=1, description="Remediation action name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")
    incident_id: Optional[str] = Field(None, description="Identifier of the incident triggering remediation")
    remediation_id: Optional[str] = Field(None, description="Identifier of the remediation approval record")


class RemediationExecutionResponse(BaseModel):
    """Response model for remediation execution outcome conforming to API Contract §6.1."""
    status: str = Field(..., description="Execution status: success or failed")
    message: str = Field(..., description="Human-readable outcome message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Action-specific execution details")

"""Remediation schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import RemediationStatus
from app.schemas.common import Page, to_iso


class RemediationCreate(BaseModel):
    """Request body for creating a remediation proposal."""

    action: str = Field(min_length=1, max_length=64)
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(default="", max_length=2000)


class RemediationDecision(BaseModel):
    """Request body for an approval or rejection decision."""

    note: str | None = Field(default=None, max_length=2000)


class RemediationRead(BaseModel):
    """Remediation representation returned by the API."""

    id: str
    incident_id: str
    action: str
    target_service: str
    parameters: dict[str, Any]
    risk_level: str
    requires_human_approval: bool
    status: RemediationStatus
    rationale: str
    approved_by: str | None = None
    approved_at: str | None = None
    rejected_by: str | None = None
    rejected_at: str | None = None
    executed_at: str | None = None
    execution_result: dict[str, Any] | None = None
    incident_status: str | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, remediation, incident_status: str | None = None) -> RemediationRead:
        """Build the response object from an ORM instance."""
        return cls(
            id=remediation.id,
            incident_id=remediation.incident_id,
            action=remediation.action,
            target_service=remediation.target_service,
            parameters=remediation.parameters or {},
            risk_level=remediation.risk_level,
            requires_human_approval=remediation.requires_human_approval,
            status=remediation.status,
            rationale=remediation.rationale,
            approved_by=remediation.approved_by,
            approved_at=to_iso(remediation.approved_at),
            rejected_by=remediation.rejected_by,
            rejected_at=to_iso(remediation.rejected_at),
            executed_at=to_iso(remediation.executed_at),
            execution_result=remediation.execution_result,
            incident_status=incident_status,
            created_at=to_iso(remediation.created_at),
            updated_at=to_iso(remediation.updated_at),
        )


class RemediationList(Page[RemediationRead]):
    """List response for remediations."""

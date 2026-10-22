"""Investigation and RCA schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import Page


class InvestigateRequest(BaseModel):
    """Request body for running an investigation."""

    scenario_id: str | None = Field(default=None, max_length=100)


class HypothesisRead(BaseModel):
    """Hypothesis representation returned by the API."""

    id: str
    kind: str
    cause: str
    explanation: str
    confidence: float
    evidence_ids: list[str]
    recommended_action_type: str | None = None


class RemediationProposal(BaseModel):
    """A proposed, not yet approved, remediation."""

    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    rationale: str = ""


class InvestigationRead(BaseModel):
    """Investigation report returned by the API."""

    id: str
    incident_id: str
    status: str
    summary: str
    root_cause_hypotheses: list[HypothesisRead]
    alternative_hypotheses: list[HypothesisRead]
    recommended_checks: list[str]
    proposed_remediations: list[RemediationProposal]
    knowledge_sources: list[str]
    evidence_ids: list[str]
    llm_used: bool
    provider: str
    model: str | None = None
    warnings: list[str]
    created_at: str


class InvestigationList(Page[InvestigationRead]):
    """List response for investigations."""

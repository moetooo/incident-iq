"""Structured RCA output models shared by the LLM and the fallback engine."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class GeneratedHypothesis(BaseModel):
    """A single candidate cause produced by the analysis."""

    cause: str = Field(min_length=1, max_length=500)
    explanation: str = Field(default="", max_length=4000)
    confidence: float = 0.0
    evidence_ids: list[str] = Field(default_factory=list)
    recommended_action_type: str | None = None

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, value: float) -> float:
        return min(max(float(value), 0.0), 1.0)

    @field_validator("evidence_ids")
    @classmethod
    def _clean_evidence_ids(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            if isinstance(item, str):
                item = item.strip()
                if item and item not in cleaned:
                    cleaned.append(item)
        return cleaned


class GeneratedRemediation(BaseModel):
    """A proposed remediation action. Never executed by the analysis step."""

    action: str = Field(min_length=1, max_length=64)
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    rationale: str = Field(default="", max_length=2000)


class GeneratedReport(BaseModel):
    """The full RCA report produced by the analysis engine."""

    summary: str = Field(default="", max_length=4000)
    root_cause_hypotheses: list[GeneratedHypothesis] = Field(default_factory=list)
    alternative_hypotheses: list[GeneratedHypothesis] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    proposed_remediations: list[GeneratedRemediation] = Field(default_factory=list)
    knowledge_sources: list[str] = Field(default_factory=list)


HYPOTHESIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cause": {"type": "string"},
        "explanation": {"type": "string"},
        "confidence": {"type": "number"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "recommended_action_type": {"type": "string"},
    },
    "required": [
        "cause",
        "explanation",
        "confidence",
        "evidence_ids",
        "recommended_action_type",
    ],
}

REMEDIATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "parameters": {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "instances": {"type": "integer"},
            },
            "required": [],
        },
        "risk_level": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["action", "parameters", "risk_level", "rationale"],
}


def gemini_response_schema() -> dict[str, Any]:
    """Return the flat JSON schema sent to Gemini.

    The schema is written without ``$ref``/``$defs`` because the Gemini
    structured-output implementation supports only a subset of JSON Schema.
    """
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "root_cause_hypotheses": {"type": "array", "items": HYPOTHESIS_SCHEMA},
            "alternative_hypotheses": {"type": "array", "items": HYPOTHESIS_SCHEMA},
            "recommended_checks": {"type": "array", "items": {"type": "string"}},
            "proposed_remediations": {"type": "array", "items": REMEDIATION_SCHEMA},
        },
        "required": [
            "summary",
            "root_cause_hypotheses",
            "alternative_hypotheses",
            "recommended_checks",
            "proposed_remediations",
        ],
    }

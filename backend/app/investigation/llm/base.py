"""Provider interface for the incident analysis engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.investigation.llm.schemas import GeneratedReport


@dataclass(frozen=True)
class EvidenceItem:
    """A single evidence item prepared for the analysis engine."""

    id: str
    type: str
    source: str
    timestamp: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5

    def to_prompt_line(self) -> str:
        """Return the compact representation used in the prompt."""
        return (
            f"[{self.id}] type={self.type} source={self.source} "
            f"timestamp={self.timestamp} confidence={self.confidence:.2f}\n"
            f"  summary: {self.summary}"
        )


@dataclass(frozen=True)
class AnalysisRequest:
    """Everything the analysis engine needs to reason about an incident."""

    incident_id: str
    title: str
    service: str
    severity: str
    description: str
    evidence: list[EvidenceItem]


class LLMProviderError(Exception):
    """Raised when a provider call cannot produce a usable report."""

    def __init__(self, message: str, reason: str = "provider_error") -> None:
        super().__init__(message)
        self.message = message
        self.reason = reason


class LLMProvider(ABC):
    """Interface implemented by every analysis provider."""

    name: str = "provider"
    model: str | None = None

    @abstractmethod
    def analyze(self, request: AnalysisRequest) -> GeneratedReport:
        """Return a structured RCA report for the request."""
        raise NotImplementedError

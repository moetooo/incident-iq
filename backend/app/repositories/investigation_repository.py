"""Investigation, step and hypothesis repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.models.enums import HypothesisKind
from app.models.investigation import Hypothesis, Investigation, InvestigationStep


class InvestigationRepository:
    """Persistence operations for investigation reports."""

    def create(
        self,
        session: Session,
        *,
        incident_id: str,
        summary: str,
        llm_used: bool,
        provider: str,
        model: str | None,
        warnings: list[str],
        recommended_checks: list[str] | None = None,
        evidence_ids: list[str] | None = None,
        knowledge_sources: list[str] | None = None,
        proposed_remediations: list[dict[str, Any]] | None = None,
        status: str = "completed",
    ) -> Investigation:
        """Create the investigation report row."""
        investigation = Investigation(
            id=new_id("investigation"),
            incident_id=incident_id,
            status=status,
            summary=summary,
            llm_used=llm_used,
            provider=provider,
            model=model,
            warnings=warnings,
            recommended_checks=recommended_checks or [],
            evidence_ids=evidence_ids or [],
            knowledge_sources=knowledge_sources or [],
            proposed_remediations=proposed_remediations or [],
        )
        session.add(investigation)
        session.flush()
        return investigation

    def add_step(
        self,
        session: Session,
        *,
        investigation_id: str,
        incident_id: str,
        step_index: int,
        agent_node: str,
        action: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> InvestigationStep:
        """Append an ordered pipeline step."""
        step = InvestigationStep(
            id=new_id("step"),
            investigation_id=investigation_id,
            incident_id=incident_id,
            step_index=step_index,
            agent_node=agent_node,
            action=action,
            summary=summary,
            step_metadata=metadata or {},
        )
        session.add(step)
        session.flush()
        return step

    def add_hypothesis(
        self,
        session: Session,
        *,
        investigation_id: str,
        incident_id: str,
        kind: HypothesisKind,
        cause: str,
        explanation: str,
        confidence: float,
        evidence_ids: list[str],
        recommended_action_type: str | None,
    ) -> Hypothesis:
        """Persist a single hypothesis."""
        hypothesis = Hypothesis(
            id=new_id("hypothesis"),
            investigation_id=investigation_id,
            incident_id=incident_id,
            kind=kind.value,
            cause=cause,
            explanation=explanation,
            confidence=confidence,
            evidence_ids=evidence_ids,
            recommended_action_type=recommended_action_type,
        )
        session.add(hypothesis)
        session.flush()
        return hypothesis

    def list_for_incident(self, session: Session, incident_id: str) -> list[Investigation]:
        """Return the investigations of an incident, newest first."""
        statement = (
            select(Investigation)
            .where(Investigation.incident_id == incident_id)
            .order_by(Investigation.created_at.desc(), Investigation.id.desc())
        )
        return list(session.execute(statement).scalars().all())

    def get(self, session: Session, investigation_id: str) -> Investigation | None:
        """Return a single investigation by id."""
        return session.get(Investigation, investigation_id)

    def hypotheses_for(
        self, session: Session, investigation_id: str
    ) -> tuple[list[Hypothesis], list[Hypothesis]]:
        """Return the root-cause and alternative hypotheses of an investigation."""
        statement = (
            select(Hypothesis)
            .where(Hypothesis.investigation_id == investigation_id)
            .order_by(Hypothesis.confidence.desc(), Hypothesis.id.asc())
        )
        rows = list(session.execute(statement).scalars().all())
        root_causes = [row for row in rows if row.kind == HypothesisKind.ROOT_CAUSE.value]
        alternatives = [row for row in rows if row.kind == HypothesisKind.ALTERNATIVE.value]
        return root_causes, alternatives

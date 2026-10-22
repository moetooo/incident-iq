"""Remediation and audit log repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.models.enums import RemediationStatus
from app.models.remediation import AuditLog, RemediationAction


class RemediationRepository:
    """Persistence operations for remediation actions and audit entries."""

    def create(
        self,
        session: Session,
        *,
        incident_id: str,
        action: str,
        target_service: str,
        parameters: dict[str, Any],
        risk_level: str,
        rationale: str,
        requires_human_approval: bool = True,
    ) -> RemediationAction:
        """Create a remediation proposal in ``pending_approval`` state."""
        remediation = RemediationAction(
            id=new_id("remediation"),
            incident_id=incident_id,
            action=action,
            target_service=target_service,
            parameters=parameters,
            risk_level=risk_level,
            requires_human_approval=requires_human_approval,
            status=RemediationStatus.PENDING_APPROVAL.value,
            rationale=rationale,
        )
        session.add(remediation)
        session.flush()
        return remediation

    def get(self, session: Session, remediation_id: str) -> RemediationAction | None:
        """Return a remediation by id."""
        return session.get(RemediationAction, remediation_id)

    def list_for_incident(self, session: Session, incident_id: str) -> list[RemediationAction]:
        """Return the remediations of an incident, newest first."""
        statement = (
            select(RemediationAction)
            .where(RemediationAction.incident_id == incident_id)
            .order_by(RemediationAction.created_at.desc(), RemediationAction.id.desc())
        )
        return list(session.execute(statement).scalars().all())

    def add_audit(
        self,
        session: Session,
        *,
        action_id: str,
        incident_id: str,
        actor: str,
        event_type: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Append an audit entry for a remediation lifecycle event."""
        entry = AuditLog(
            id=new_id("audit"),
            action_id=action_id,
            incident_id=incident_id,
            actor=actor,
            event_type=event_type,
            details=details or {},
        )
        session.add(entry)
        session.flush()
        return entry

"""Remediation lifecycle: proposal, approval, rejection and execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.errors import ConflictError
from app.core.logging import get_logger
from app.models.enums import IncidentStatus, RemediationStatus
from app.models.incident import Incident
from app.models.remediation import RemediationAction
from app.remediation.allowlist import get_spec
from app.repositories.incident_repository import IncidentRepository
from app.repositories.remediation_repository import RemediationRepository
from app.services.remediation_dispatcher import RemediationDispatcher

UTC = timezone.utc

logger = get_logger(__name__)


class RemediationService:
    """Enforces the approval workflow around simulated remediations."""

    def __init__(
        self,
        *,
        remediation_repository: RemediationRepository,
        incident_repository: IncidentRepository,
        dispatcher: RemediationDispatcher,
    ) -> None:
        self.remediation_repository = remediation_repository
        self.incident_repository = incident_repository
        self.dispatcher = dispatcher

    def create_proposal(
        self,
        session,
        incident: Incident,
        *,
        action: str,
        parameters: dict[str, Any] | None,
        rationale: str,
        actor: str = "operator",
    ) -> RemediationAction:
        """Create a remediation proposal. The action is never executed here."""
        if incident.status == IncidentStatus.RESOLVED.value:
            raise ConflictError(
                "The incident is already resolved and cannot receive new remediations",
                details={"incident_id": incident.id, "status": incident.status},
            )

        spec = get_spec(action)
        validated_parameters = spec.validate_parameters(parameters)

        remediation = self.remediation_repository.create(
            session,
            incident_id=incident.id,
            action=spec.action,
            target_service=incident.service,
            parameters=validated_parameters,
            risk_level=spec.risk_level,
            rationale=rationale,
            requires_human_approval=True,
        )
        self.remediation_repository.add_audit(
            session,
            action_id=remediation.id,
            incident_id=incident.id,
            actor=actor,
            event_type="created",
            details={"action": spec.action, "parameters": validated_parameters},
        )
        return remediation

    def approve(
        self,
        session,
        remediation: RemediationAction,
        *,
        operator_id: str,
        note: str | None = None,
    ) -> RemediationAction:
        """Record an explicit approval and dispatch the action."""
        self._require_status(remediation, RemediationStatus.PENDING_APPROVAL)

        remediation.status = RemediationStatus.APPROVED.value
        remediation.approved_by = operator_id
        remediation.approved_at = datetime.now(UTC)
        session.flush()

        self.remediation_repository.add_audit(
            session,
            action_id=remediation.id,
            incident_id=remediation.incident_id,
            actor=operator_id,
            event_type="approved",
            details={"note": note or "", "action": remediation.action},
        )

        return self.execute(session, remediation, actor=operator_id)

    def reject(
        self,
        session,
        remediation: RemediationAction,
        *,
        operator_id: str,
        note: str | None = None,
    ) -> RemediationAction:
        """Record an explicit rejection. No action is dispatched."""
        self._require_status(remediation, RemediationStatus.PENDING_APPROVAL)

        remediation.status = RemediationStatus.REJECTED.value
        remediation.rejected_by = operator_id
        remediation.rejected_at = datetime.now(UTC)
        session.flush()

        self.remediation_repository.add_audit(
            session,
            action_id=remediation.id,
            incident_id=remediation.incident_id,
            actor=operator_id,
            event_type="rejected",
            details={"note": note or "", "action": remediation.action},
        )

        incident = self.incident_repository.get(session, remediation.incident_id)
        if incident is not None and incident.status == IncidentStatus.AWAITING_APPROVAL.value:
            self.incident_repository.set_status(
                session, incident, IncidentStatus.HYPOTHESIS_FORMED
            )

        return remediation

    def execute(
        self, session, remediation: RemediationAction, *, actor: str = "operator"
    ) -> RemediationAction:
        """Dispatch an approved remediation and record the outcome."""
        self._require_status(remediation, RemediationStatus.APPROVED)

        remediation.status = RemediationStatus.EXECUTING.value
        session.flush()

        self.remediation_repository.add_audit(
            session,
            action_id=remediation.id,
            incident_id=remediation.incident_id,
            actor=actor,
            event_type="execution_started",
            details={"action": remediation.action},
        )

        incident = self.incident_repository.get(session, remediation.incident_id)
        if incident is not None:
            self.incident_repository.set_status(session, incident, IncidentStatus.REMEDIATING)

        result = self.dispatcher.dispatch(remediation)

        action_succeeded = result.get("outcome") == "success"
        service_healthy = result.get("service_healthy")
        verification_passed = bool(action_succeeded and service_healthy is not False)
        result["verification_passed"] = verification_passed
        if action_succeeded and service_healthy is False:
            result["verification_message"] = (
                "The action was applied but the service is still reporting an unhealthy "
                "state; the incident remains open."
            )

        remediation.status = (
            RemediationStatus.SUCCESS.value
            if action_succeeded
            else RemediationStatus.FAILED.value
        )
        remediation.executed_at = datetime.now(UTC)
        remediation.execution_result = result
        session.flush()

        self.remediation_repository.add_audit(
            session,
            action_id=remediation.id,
            incident_id=remediation.incident_id,
            actor=actor,
            event_type=(
                "execution_succeeded"
                if remediation.status == RemediationStatus.SUCCESS.value
                else "execution_failed"
            ),
            details={
                "outcome": result.get("outcome"),
                "message": result.get("message"),
                "verification_passed": verification_passed,
            },
        )

        if incident is not None:
            if verification_passed:
                self.incident_repository.set_status(
                    session, incident, IncidentStatus.RESOLVED, resolved=True
                )
            elif incident.status == IncidentStatus.REMEDIATING.value:
                # The incident stays open until the service is verified healthy.
                self.incident_repository.set_status(
                    session, incident, IncidentStatus.AWAITING_APPROVAL
                )

        logger.info(
            "remediation_executed",
            extra={
                "remediation_id": remediation.id,
                "incident_id": remediation.incident_id,
                "action": remediation.action,
                "status": remediation.status,
            },
        )
        return remediation

    @staticmethod
    def _require_status(
        remediation: RemediationAction, expected: RemediationStatus
    ) -> None:
        """Raise a conflict error when the remediation is in the wrong state."""
        if remediation.status != expected.value:
            raise ConflictError(
                (
                    f"Remediation '{remediation.id}' is '{remediation.status}' and cannot "
                    f"perform this transition (expected '{expected.value}')."
                ),
                details={
                    "remediation_id": remediation.id,
                    "status": remediation.status,
                    "expected_status": expected.value,
                },
            )

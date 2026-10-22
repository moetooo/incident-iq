"""Dispatch of allowlisted simulated remediation actions."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.models.remediation import RemediationAction
from app.remediation.allowlist import get_spec
from app.services.simulator_client import SimulatorClient

logger = get_logger(__name__)

SUCCESS_STATUSES = {"success", "ok", "applied", "completed", "succeeded"}


class RemediationDispatcher:
    """Sends an allowlisted action to the simulator.

    The dispatcher never executes shell commands and never reaches outside the
    demo environment. Only actions on the server-side allowlist can be
    dispatched.
    """

    def __init__(self, simulator_client: SimulatorClient) -> None:
        self.simulator_client = simulator_client

    def dispatch(self, remediation: RemediationAction) -> dict[str, Any]:
        """Dispatch the action and return the execution outcome."""
        spec = get_spec(remediation.action)
        parameters = spec.validate_parameters(remediation.parameters)

        try:
            payload = self.simulator_client.execute_remediation(
                action=remediation.action,
                parameters=parameters,
                incident_id=remediation.incident_id,
                remediation_id=remediation.id,
            )
        except Exception as exc:
            logger.warning(
                "remediation_dispatch_failed",
                extra={"remediation_id": remediation.id, "action": remediation.action},
            )
            return {
                "outcome": "failed",
                "message": f"The simulator could not apply the action: {exc}",
                "details": {},
            }

        status = str(payload.get("status", "success")).strip().lower()
        outcome = "success" if status in SUCCESS_STATUSES else "failed"
        details = payload.get("details")
        if not isinstance(details, dict):
            details = {"raw": details} if details is not None else {}

        health_status = self.simulator_client.health_status()

        return {
            "outcome": outcome,
            "message": str(payload.get("message", "")),
            "details": details,
            "simulator_status": status,
            "service_healthy": health_status == "ok",
            "service_health_status": health_status,
        }

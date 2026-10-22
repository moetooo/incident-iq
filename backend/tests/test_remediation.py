"""Remediation lifecycle tests."""

from __future__ import annotations

from tests.conftest import FakeSimulatorClient

DATABASE_EVIDENCE = [
    {
        "type": "log",
        "source": "payment-api",
        "timestamp": "2026-01-01T10:00:00Z",
        "summary": "Database connection timeout: too many connections in the pool",
        "details": {"level": "error"},
    }
]


def _create_incident(client, incident_payload) -> str:
    return client.post("/api/v1/incidents", json=incident_payload).json()["id"]


def _create_remediation(client, incident_id, action="restart_demo_service", parameters=None):
    payload = {"action": action, "parameters": parameters or {}, "rationale": "test"}
    return client.post(f"/api/v1/incidents/{incident_id}/remediations", json=payload)


def test_create_remediation_returns_a_pending_proposal(client, incident_payload):
    incident_id = _create_incident(client, incident_payload)

    response = _create_remediation(client, incident_id)

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("rem_")
    assert body["incident_id"] == incident_id
    assert body["action"] == "restart_demo_service"
    assert body["status"] == "pending_approval"
    assert body["requires_human_approval"] is True
    assert body["approved_by"] is None


def test_create_remediation_rejects_an_unknown_action(client, incident_payload):
    incident_id = _create_incident(client, incident_payload)

    response = _create_remediation(client, incident_id, action="rm -rf /")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "UNSUPPORTED_ACTION"
    assert "allowed_actions" in error["details"]


def test_create_remediation_rejects_invalid_parameters(client, incident_payload):
    incident_id = _create_incident(client, incident_payload)

    response = _create_remediation(
        client, incident_id, action="scale_demo_instances", parameters={"instances": 99}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARAMETERS"


def test_create_remediation_rejects_unknown_parameters(client, incident_payload):
    incident_id = _create_incident(client, incident_payload)

    response = _create_remediation(
        client, incident_id, action="restart_demo_service", parameters={"command": "rm -rf /"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARAMETERS"


def test_approve_requires_an_operator_identity(client, incident_payload):
    incident_id = _create_incident(client, incident_payload)
    remediation_id = _create_remediation(client, incident_id).json()["id"]

    response = client.post(f"/api/v1/remediations/{remediation_id}/approve", json={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_approve_executes_the_action_and_resolves_the_incident(make_client, incident_payload):
    simulator = FakeSimulatorClient()
    client = make_client(simulator)
    incident_id = _create_incident(client, incident_payload)
    remediation_id = _create_remediation(client, incident_id).json()["id"]

    response = client.post(
        f"/api/v1/remediations/{remediation_id}/approve",
        json={"note": "confirmed"},
        headers={"X-Operator-Id": "operator@example.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["approved_by"] == "operator@example.com"
    assert body["approved_at"] is not None
    assert body["executed_at"] is not None
    assert body["execution_result"]["outcome"] == "success"
    assert body["incident_status"] == "resolved"

    assert simulator.executed[0]["action"] == "restart_demo_service"
    assert simulator.executed[0]["incident_id"] == incident_id

    incident = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert incident["status"] == "resolved"
    assert incident["resolved_at"] is not None


def test_approve_cannot_be_repeated(client, incident_payload):
    incident_id = _create_incident(client, incident_payload)
    remediation_id = _create_remediation(client, incident_id).json()["id"]

    first = client.post(
        f"/api/v1/remediations/{remediation_id}/approve",
        json={},
        headers={"X-Operator-Id": "operator@example.com"},
    )
    second = client.post(
        f"/api/v1/remediations/{remediation_id}/approve",
        json={},
        headers={"X-Operator-Id": "operator@example.com"},
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_reject_records_the_decision_and_executes_nothing(make_client, incident_payload):
    simulator = FakeSimulatorClient()
    client = make_client(simulator)
    incident_id = _create_incident(client, incident_payload)
    remediation_id = _create_remediation(client, incident_id).json()["id"]

    response = client.post(
        f"/api/v1/remediations/{remediation_id}/reject",
        json={"note": "not related"},
        headers={"X-Operator-Id": "operator@example.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    # The incident was never investigated, so it stays in its current state.
    assert body["incident_status"] == "triggered"
    assert body["rejected_by"] == "operator@example.com"
    assert body["rejected_at"] is not None
    assert body["executed_at"] is None
    assert simulator.executed == []


def test_execute_requires_an_approved_remediation(client, incident_payload):
    incident_id = _create_incident(client, incident_payload)
    remediation_id = _create_remediation(client, incident_id).json()["id"]

    response = client.post(f"/api/v1/remediations/{remediation_id}/execute", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_failed_execution_keeps_the_incident_open(make_client, incident_payload):
    simulator = FakeSimulatorClient(
        remediation_response={"status": "failed", "message": "not applied"}
    )
    client = make_client(simulator)
    incident_id = _create_incident(client, incident_payload)
    remediation_id = _create_remediation(client, incident_id).json()["id"]

    response = client.post(
        f"/api/v1/remediations/{remediation_id}/approve",
        json={},
        headers={"X-Operator-Id": "operator@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"

    incident = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert incident["status"] == "awaiting_approval"
    assert incident["resolved_at"] is None


def test_approve_returns_404_for_an_unknown_remediation(client):
    response = client.post(
        "/api/v1/remediations/rem_missing/approve",
        json={},
        headers={"X-Operator-Id": "operator@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REMEDIATION_NOT_FOUND"


def test_remediation_of_an_unknown_incident_returns_404(client):
    response = client.post(
        "/api/v1/incidents/inc_missing/remediations",
        json={"action": "restart_demo_service", "parameters": {}, "rationale": ""},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INCIDENT_NOT_FOUND"


def test_incident_stays_open_when_the_service_is_still_unhealthy(make_client, incident_payload):
    """Regression: an applied action must not close the incident when the
    simulator still reports an unhealthy service."""
    simulator = FakeSimulatorClient(
        healthy=False,
        remediation_response={"status": "success", "message": "Scaled payment-api to 4 instances"},
    )
    client = make_client(simulator)
    incident_id = _create_incident(client, incident_payload)
    remediation_id = _create_remediation(
        client, incident_id, action="scale_demo_instances", parameters={"instances": 4}
    ).json()["id"]

    response = client.post(
        f"/api/v1/remediations/{remediation_id}/approve",
        json={},
        headers={"X-Operator-Id": "operator@example.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success", "the action itself was applied"
    assert body["execution_result"]["verification_passed"] is False
    assert body["execution_result"]["service_healthy"] is False
    assert body["incident_status"] == "awaiting_approval"

    incident = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert incident["status"] == "awaiting_approval"
    assert incident["resolved_at"] is None


def test_audit_trail_records_the_lifecycle(client, incident_payload, session):
    incident_id = _create_incident(client, incident_payload)
    remediation_id = _create_remediation(client, incident_id).json()["id"]

    client.post(
        f"/api/v1/remediations/{remediation_id}/approve",
        json={},
        headers={"X-Operator-Id": "operator@example.com"},
    )

    from sqlalchemy import select

    from app.models.remediation import AuditLog

    entries = list(
        session.execute(
            select(AuditLog).where(AuditLog.action_id == remediation_id)
        ).scalars()
    )

    event_types = [entry.event_type for entry in entries]
    assert "created" in event_types
    assert "approved" in event_types
    assert "execution_succeeded" in event_types
    assert any(entry.actor == "operator@example.com" for entry in entries)

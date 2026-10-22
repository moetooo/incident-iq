"""Evidence collection tests."""

from __future__ import annotations

from tests.conftest import FakeSimulatorClient

DATABASE_EVIDENCE = [
    {
        "id": "sim_ev_1",
        "type": "log",
        "source": "payment-api",
        "timestamp": "2026-01-01T10:00:00Z",
        "summary": "Database connection timeout while processing payment request",
        "details": {"level": "error", "message": "connection timed out"},
    }
]

DEPLOYMENT_EVIDENCE = [
    {
        "type": "deployment",
        "source": "payment-api",
        "timestamp": "2026-01-01T09:55:00Z",
        "summary": "Deployed release v2.4.1",
        "details": {"version": "v2.4.1"},
    }
]


def test_collect_evidence_persists_normalised_items(make_client, incident_payload):
    simulator = FakeSimulatorClient(evidence=DATABASE_EVIDENCE, deployments=DEPLOYMENT_EVIDENCE)
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    response = client.post(
        f"/api/v1/incidents/{incident_id}/evidence", json={"scenario_id": "database_failure"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["collected"] == 2
    assert body["stored"] == 2
    assert body["warnings"] == []

    types = {item["type"] for item in body["items"]}
    assert types == {"log", "deployment"}
    assert all(item["id"].startswith("ev_") for item in body["items"])
    assert all(item["incident_id"] == incident_id for item in body["items"])
    assert all(item["timestamp"].endswith("Z") for item in body["items"])


def test_collect_evidence_deduplicates_repeated_collection(make_client, incident_payload):
    simulator = FakeSimulatorClient(evidence=DATABASE_EVIDENCE)
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    first = client.post(f"/api/v1/incidents/{incident_id}/evidence", json={})
    second = client.post(f"/api/v1/incidents/{incident_id}/evidence", json={})

    assert first.json()["stored"] == 1
    assert second.json()["stored"] == 0
    assert second.json()["collected"] == 1

    listed = client.get(f"/api/v1/incidents/{incident_id}/evidence").json()
    assert listed["total"] == 1


def test_collect_evidence_maps_the_simulator_deployment_shape(make_client, incident_payload):
    simulator = FakeSimulatorClient(
        deployments=[
            {
                "id": "dep_1",
                "version": "v2.4.1",
                "service": "payment-api",
                "deployed_at": "2026-01-01T09:55:00Z",
                "deployed_by": "ci-pipeline",
                "status": "active",
                "commit_sha": "abc1234",
                "changelog": "Bumped connection pool timeout",
            }
        ]
    )
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    response = client.post(f"/api/v1/incidents/{incident_id}/evidence", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["warnings"] == []
    assert body["stored"] == 1
    item = body["items"][0]
    assert item["type"] == "deployment"
    assert item["source"] == "payment-api"
    assert item["timestamp"] == "2026-01-01T09:55:00Z"
    assert item["summary"] == "Bumped connection pool timeout"
    assert item["details"]["version"] == "v2.4.1"


def test_collect_evidence_skips_unsupported_types_with_a_warning(make_client, incident_payload):
    simulator = FakeSimulatorClient(
        evidence=[
            {"type": "quantum_flux", "source": "payment-api", "summary": "unknown signal"},
            *DATABASE_EVIDENCE,
        ]
    )
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    response = client.post(f"/api/v1/incidents/{incident_id}/evidence", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["stored"] == 1
    assert len(body["warnings"]) == 1
    assert "quantum_flux" in body["warnings"][0]


def test_collect_evidence_reports_an_unreachable_simulator(make_client, incident_payload):
    simulator = FakeSimulatorClient(unavailable=True)
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    response = client.post(f"/api/v1/incidents/{incident_id}/evidence", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["stored"] == 0
    assert body["warnings"]


def test_collect_evidence_returns_404_for_an_unknown_incident(client):
    response = client.post("/api/v1/incidents/inc_missing/evidence", json={})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INCIDENT_NOT_FOUND"


def test_list_evidence_returns_the_stored_items(make_client, incident_payload):
    simulator = FakeSimulatorClient(evidence=DATABASE_EVIDENCE)
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]
    client.post(f"/api/v1/incidents/{incident_id}/evidence", json={})

    response = client.get(f"/api/v1/incidents/{incident_id}/evidence")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["type"] == "log"
    assert body["items"][0]["summary"].startswith("Database connection timeout")

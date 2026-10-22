"""Incident API tests."""

from __future__ import annotations


def test_create_incident_returns_201(client, incident_payload):
    response = client.post("/api/v1/incidents", json=incident_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("inc_")
    assert body["title"] == incident_payload["title"]
    assert body["service"] == incident_payload["service"]
    assert body["severity"] == "high"
    assert body["status"] == "triggered"
    assert body["created_at"].endswith("Z")
    assert body["resolved_at"] is None


def test_list_incidents_returns_items_and_total(client, incident_payload):
    client.post("/api/v1/incidents", json=incident_payload)
    client.post("/api/v1/incidents", json={**incident_payload, "severity": "low"})

    response = client.get("/api/v1/incidents")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_list_incidents_filters_by_status_and_severity(client, incident_payload):
    client.post("/api/v1/incidents", json=incident_payload)
    client.post("/api/v1/incidents", json={**incident_payload, "severity": "low"})

    response = client.get("/api/v1/incidents", params={"severity": "low"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["severity"] == "low"


def test_list_incidents_rejects_an_unknown_severity(client):
    response = client.get("/api/v1/incidents", params={"severity": "catastrophic"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_incident_rejects_an_invalid_payload(client):
    response = client.post(
        "/api/v1/incidents",
        json={"title": "", "service": "payment-api", "severity": "high"},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"].startswith("req_")


def test_get_incident_returns_404_for_an_unknown_id(client):
    response = client.get("/api/v1/incidents/inc_missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INCIDENT_NOT_FOUND"


def test_get_incident_returns_the_stored_incident(client, incident_payload):
    created = client.post("/api/v1/incidents", json=incident_payload).json()

    response = client.get(f"/api/v1/incidents/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created

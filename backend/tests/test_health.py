"""Health endpoint tests."""

from __future__ import annotations


def test_health_reports_service_state(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"]
    assert body["database"] == "ok"
    assert body["llm"]["configured"] is False
    assert body["llm"]["model"]


def test_health_is_available_under_the_api_prefix(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_returns_a_request_id_header(client):
    response = client.get("/health")

    assert response.headers.get("X-Request-ID", "").startswith("req_")

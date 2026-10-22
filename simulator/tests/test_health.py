def test_health_endpoint_healthy(client):
    """Verify /health returns status ok when simulator is in normal state."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "payment-api"
    assert data["scenario"] == "normal"
    assert data["healthy"] is True


def test_health_endpoint_degraded(client):
    """Verify /health returns degraded when a failure scenario is active."""
    # Trigger database failure
    trigger_resp = client.post("/demo/scenarios/database_failure/trigger")
    assert trigger_resp.status_code == 200

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    data = health_resp.json()
    assert data["status"] == "degraded"
    assert data["scenario"] == "database_failure"
    assert data["healthy"] is False

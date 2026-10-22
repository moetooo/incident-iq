def test_reset_restores_healthy_state(client):
    """Verify reset returns simulator to normal scenario and clears degraded state."""
    # 1. Trigger bad deployment
    trigger_resp = client.post("/demo/scenarios/bad_deployment/trigger")
    assert trigger_resp.status_code == 200

    # Verify degraded
    health_resp = client.get("/health")
    assert health_resp.json()["healthy"] is False
    assert health_resp.json()["version"] == "v2.4.1"

    # 2. Reset
    reset_resp = client.post("/demo/scenarios/reset")
    assert reset_resp.status_code == 200
    reset_data = reset_resp.json()
    assert reset_data["status"] == "ok"
    assert reset_data["scenario"] == "normal"

    # 3. Verify health restored
    health_after = client.get("/health").json()
    assert health_after["status"] == "ok"
    assert health_after["scenario"] == "normal"
    assert health_after["healthy"] is True
    assert health_after["version"] == "v2.4.0"

    # 4. Verify metrics restored
    metrics = client.get("/internal/metrics").json()
    assert metrics["error_rate_pct"] == 0.0
    assert metrics["active_db_connections"] == 5
    assert metrics["p95_latency_ms"] == 45.0

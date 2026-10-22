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


def test_reset_restores_complete_surface_consistency(client):
    """Verify reset restores consistency across health, evidence, deployments, metrics, and payment routes."""
    # 1. Produce multiple failure states
    client.post("/demo/scenarios/database_failure/trigger")
    fail_pay = client.post("/payments", json={"amount": 25.0})
    assert fail_pay.status_code == 503

    client.post("/demo/scenarios/bad_deployment/trigger")
    deps_pre = client.get("/internal/deployments").json()["items"]
    assert len(deps_pre) == 2

    # 2. Execute Reset
    reset_resp = client.post("/demo/scenarios/reset")
    assert reset_resp.status_code == 200

    # 3. Check health
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["healthy"] is True
    assert health["version"] == "v2.4.0"
    assert health["scenario"] == "normal"

    # 4. Check metrics
    metrics = client.get("/internal/metrics").json()
    assert metrics["error_rate_pct"] == 0.0
    assert metrics["error_count"] == 0
    assert metrics["active_db_connections"] == 5

    # 5. Check evidence
    ev_items = client.get("/internal/evidence").json()["items"]
    ev_ids = [it["id"] for it in ev_items]
    assert set(ev_ids) == {"ev_normal_state", "ev_normal_metrics", "ev_normal_log"}

    # 6. Check deployments
    deps = client.get("/internal/deployments").json()["items"]
    assert len(deps) == 1
    assert deps[0]["version"] == "v2.4.0"
    assert deps[0]["status"] == "active"

    # 7. Check payment processing
    pay_resp = client.post("/payments", json={"amount": 25.0})
    assert pay_resp.status_code == 200
    assert pay_resp.json()["status"] == "approved"

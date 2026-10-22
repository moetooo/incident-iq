import pytest


def test_list_scenarios(client):
    """Verify all scenarios are listed with active flag."""
    response = client.get("/demo/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 4
    
    ids = [s["id"] for s in scenarios]
    assert "normal" in ids
    assert "database_failure" in ids
    assert "payment_timeout" in ids
    assert "bad_deployment" in ids
    
    # By default normal is active
    normal_s = next(s for s in scenarios if s["id"] == "normal")
    assert normal_s["is_active"] is True


def test_trigger_database_failure(client):
    """Verify triggering database_failure updates scenario and generates evidence."""
    response = client.post("/demo/scenarios/database_failure/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["scenario_id"] == "database_failure"
    assert data["health_status"] == "degraded"
    assert data["evidence_count_generated"] > 0


def test_trigger_payment_timeout(client):
    """Verify triggering payment_timeout updates scenario and generates evidence."""
    response = client.post("/demo/scenarios/payment_timeout/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["scenario_id"] == "payment_timeout"
    assert data["health_status"] == "degraded"
    assert data["evidence_count_generated"] > 0


def test_trigger_bad_deployment(client):
    """Verify triggering bad_deployment updates version to v2.4.1."""
    response = client.post("/demo/scenarios/bad_deployment/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["scenario_id"] == "bad_deployment"
    assert data["health_status"] == "degraded"

    # Check deployments
    deps = client.get("/internal/deployments").json()
    assert deps["items"][0]["version"] == "v2.4.1"


def test_trigger_invalid_scenario(client):
    """Verify triggering non-existent scenario returns 400 Bad Request."""
    response = client.post("/demo/scenarios/non_existent_chaos/trigger")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "Invalid scenario_id" in data["error"]["message"]


def test_trigger_bad_deployment_is_idempotent(client):
    """Verify repeatedly triggering bad_deployment does not create duplicate deployment records or drift metrics."""
    # First trigger
    resp1 = client.post("/demo/scenarios/bad_deployment/trigger")
    assert resp1.status_code == 200

    # Second trigger
    resp2 = client.post("/demo/scenarios/bad_deployment/trigger")
    assert resp2.status_code == 200

    # Verify deployment records: only one v2.4.1 deployment should exist
    deps = client.get("/internal/deployments").json()["items"]
    v241_deployments = [d for d in deps if d["version"] == "v2.4.1"]
    assert len(v241_deployments) == 1, f"Expected 1 faulty deployment event, found {len(v241_deployments)}"
    assert len(deps) == 2  # baseline v2.4.0 + bad v2.4.1

    # Verify metrics: error counter must not accumulate/double
    metrics = client.get("/internal/metrics").json()
    assert metrics["error_count"] == 62
    assert metrics["error_rate_pct"] == 42.0


def test_repeated_trigger_does_not_accumulate_counters(client):
    """Verify repeated activation of database_failure preserves documented metrics without counter drift."""
    for _ in range(3):
        resp = client.post("/demo/scenarios/database_failure/trigger")
        assert resp.status_code == 200

    metrics = client.get("/internal/metrics").json()
    assert metrics["error_count"] == 48
    assert metrics["error_rate_pct"] == 85.0
    assert metrics["active_db_connections"] == 50
    assert metrics["db_pool_utilization_pct"] == 100.0


def test_cross_scenario_transitions_consistency(client):
    """Verify transitions between all scenarios update health, metrics, evidence, and payments consistently."""
    # 1. Normal state
    resp_norm = client.post("/demo/scenarios/normal/trigger")
    assert resp_norm.status_code == 200
    h_norm = client.get("/health").json()
    assert h_norm["scenario"] == "normal" and h_norm["healthy"] is True
    m_norm = client.get("/internal/metrics").json()
    assert m_norm["error_rate_pct"] == 0.0 and m_norm["active_db_connections"] == 5 and m_norm["p95_latency_ms"] == 45.0
    assert client.post("/payments", json={"amount": 10.0}).status_code == 200

    # 2. Transition Normal -> Database Failure
    resp_db = client.post("/demo/scenarios/database_failure/trigger")
    assert resp_db.status_code == 200
    h_db = client.get("/health").json()
    assert h_db["scenario"] == "database_failure" and h_db["healthy"] is False
    m_db = client.get("/internal/metrics").json()
    assert m_db["error_rate_pct"] == 85.0 and m_db["active_db_connections"] == 50 and m_db["p95_latency_ms"] == 850.0
    ev_db = [item["id"] for item in client.get("/internal/evidence").json()["items"]]
    assert "ev_db_pool_exhausted" in ev_db
    assert client.post("/payments", json={"amount": 10.0}).status_code == 503

    # 3. Transition Database Failure -> Payment Timeout
    resp_time = client.post("/demo/scenarios/payment_timeout/trigger")
    assert resp_time.status_code == 200
    h_time = client.get("/health").json()
    assert h_time["scenario"] == "payment_timeout" and h_time["healthy"] is False
    m_time = client.get("/internal/metrics").json()
    assert m_time["error_rate_pct"] == 65.0 and m_time["active_db_connections"] == 12 and m_time["p95_latency_ms"] == 5200.0
    ev_time = [item["id"] for item in client.get("/internal/evidence").json()["items"]]
    assert "ev_payment_latency_metric" in ev_time
    assert client.post("/payments", json={"amount": 10.0}).status_code == 504

    # 4. Transition Payment Timeout -> Bad Deployment
    resp_bad = client.post("/demo/scenarios/bad_deployment/trigger")
    assert resp_bad.status_code == 200
    h_bad = client.get("/health").json()
    assert h_bad["scenario"] == "bad_deployment" and h_bad["healthy"] is False and h_bad["version"] == "v2.4.1"
    m_bad = client.get("/internal/metrics").json()
    assert m_bad["error_rate_pct"] == 42.0 and m_bad["active_db_connections"] == 8 and m_bad["p95_latency_ms"] == 65.0
    ev_bad = [item["id"] for item in client.get("/internal/evidence").json()["items"]]
    assert "ev_bad_deploy_event" in ev_bad
    assert client.post("/payments", json={"amount": 10.0}).status_code == 500

    # 5. Transition Bad Deployment -> Normal
    resp_back_norm = client.post("/demo/scenarios/normal/trigger")
    assert resp_back_norm.status_code == 200
    h_back_norm = client.get("/health").json()
    assert h_back_norm["scenario"] == "normal" and h_back_norm["healthy"] is True and h_back_norm["version"] == "v2.4.0"
    m_back_norm = client.get("/internal/metrics").json()
    assert m_back_norm["error_rate_pct"] == 0.0 and m_back_norm["active_db_connections"] == 5 and m_back_norm["p95_latency_ms"] == 45.0
    assert client.post("/payments", json={"amount": 10.0}).status_code == 200

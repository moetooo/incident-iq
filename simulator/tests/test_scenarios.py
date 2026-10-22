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

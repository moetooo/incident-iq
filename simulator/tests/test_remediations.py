import pytest
from app.models.scenario import ScenarioId
from app.services.state_service import simulator_state_service


def test_rollback_remediation_success(client):
    """Test successful rollback of a bad deployment to stable release."""
    # First trigger bad_deployment
    trigger_resp = client.post("/demo/scenarios/bad_deployment/trigger")
    assert trigger_resp.status_code == 200
    assert client.get("/health").json()["healthy"] is False

    # Execute rollback remediation according to §6.1
    payload = {
        "action": "rollback_demo_deployment",
        "parameters": {},
        "incident_id": "inc_9f1c2d3e4a5b",
        "remediation_id": "rem_abc123def456"
    }
    response = client.post("/internal/remediations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "Rolled back" in data["message"]
    assert data["details"]["version"] == "v2.4.0"

    # Verify state across read endpoints
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["healthy"] is True
    assert health["version"] == "v2.4.0"
    assert health["scenario"] == "normal"

    deployments = client.get("/internal/deployments").json()["items"]
    faulty = next(d for d in deployments if d["id"] == "dep_v241_faulty")
    stable = next(d for d in deployments if d["id"] == "dep_v240_stable")
    assert faulty["status"] == "rolled_back"
    assert stable["status"] == "active"

    metrics = client.get("/internal/metrics").json()
    assert metrics["is_healthy"] is True
    assert metrics["error_rate_pct"] == 0.0

    # Verify payments now succeed
    pay_resp = client.post("/payments", json={"amount": 99.99, "currency": "USD"})
    assert pay_resp.status_code == 200
    assert pay_resp.json()["status"] == "approved"


def test_rollback_remediation_custom_version(client):
    """Test rollback requesting a specific target version via parameters.version."""
    client.post("/demo/scenarios/bad_deployment/trigger")

    payload = {
        "action": "rollback_demo_deployment",
        "parameters": {"version": "v2.3.0"},
        "incident_id": "inc_test_custom_ver"
    }
    response = client.post("/internal/remediations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["details"]["version"] == "v2.3.0"

    health = client.get("/health").json()
    assert health["healthy"] is True
    assert health["version"] == "v2.3.0"


def test_restart_demo_service_success(client):
    """Test restart_demo_service clears degraded scenario and restores healthy baseline."""
    client.post("/demo/scenarios/database_failure/trigger")
    assert client.get("/health").json()["healthy"] is False

    payload = {
        "action": "restart_demo_service",
        "parameters": {}
    }
    response = client.post("/internal/remediations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["details"]["restarted"] is True

    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["healthy"] is True
    assert health["scenario"] == "normal"

    metrics = client.get("/internal/metrics").json()
    assert metrics["is_healthy"] is True
    assert metrics["active_db_connections"] == 5


def test_scale_demo_instances_success(client):
    """Test scale_demo_instances updates instance count within allowed range."""
    payload = {
        "action": "scale_demo_instances",
        "parameters": {"instances": 4}
    }
    response = client.post("/internal/remediations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["details"]["instances"] == 4
    assert simulator_state_service.get_instance_count() == 4


def test_clear_demo_cache_success(client):
    """Test clear_demo_cache execution."""
    payload = {
        "action": "clear_demo_cache",
        "parameters": {}
    }
    response = client.post("/internal/remediations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["details"]["cleared"] is True
    assert simulator_state_service.get_cache_cleared_at() is not None


def test_unsupported_action_rejected(client):
    """Test unsupported action is safely rejected with HTTP 422 and UNSUPPORTED_ACTION code."""
    payload = {
        "action": "drop_production_tables",
        "parameters": {}
    }
    response = client.post("/internal/remediations", json=payload)
    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "UNSUPPORTED_ACTION"
    assert "not on the remediation allowlist" in data["error"]["message"]
    assert "rollback_demo_deployment" in data["error"]["details"]["allowed_actions"]


def test_malformed_request_missing_action(client):
    """Test missing required action field produces VALIDATION_ERROR without changing state."""
    response = client.post("/internal/remediations", json={"parameters": {}})
    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_malformed_request_invalid_parameters(client):
    """Test invalid parameters for an action are rejected with INVALID_PARAMETERS."""
    # scale_demo_instances with missing required instances
    resp1 = client.post("/internal/remediations", json={"action": "scale_demo_instances", "parameters": {}})
    assert resp1.status_code == 422
    assert resp1.json()["error"]["code"] == "INVALID_PARAMETERS"

    # scale_demo_instances with instances out of bounds (1..10)
    resp2 = client.post("/internal/remediations", json={"action": "scale_demo_instances", "parameters": {"instances": 25}})
    assert resp2.status_code == 422
    assert resp2.json()["error"]["code"] == "INVALID_PARAMETERS"

    # scale_demo_instances with non-int instances
    resp3 = client.post("/internal/remediations", json={"action": "scale_demo_instances", "parameters": {"instances": "high"}})
    assert resp3.status_code == 422
    assert resp3.json()["error"]["code"] == "INVALID_PARAMETERS"

    # rollback_demo_deployment with empty version
    resp4 = client.post("/internal/remediations", json={"action": "rollback_demo_deployment", "parameters": {"version": ""}})
    assert resp4.status_code == 422
    assert resp4.json()["error"]["code"] == "INVALID_PARAMETERS"


def test_simulated_execution_failure_leaves_state_consistent(client):
    """Test simulated execution failure returns failed status and does not falsely claim recovery."""
    # Start in bad_deployment state
    client.post("/demo/scenarios/bad_deployment/trigger")
    assert client.get("/health").json()["healthy"] is False

    payload = {
        "action": "rollback_demo_deployment",
        "parameters": {"simulate_failure": True}
    }
    response = client.post("/internal/remediations", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Must return status="failed" and must not claim success
    assert data["status"] == "failed"
    assert "failure" in data["message"].lower()

    # Service MUST still be degraded and NOT falsely marked healthy
    health = client.get("/health").json()
    assert health["healthy"] is False
    assert health["scenario"] == "bad_deployment"
    assert health["status"] == "degraded"

    # Payments must continue failing
    pay_resp = client.post("/payments", json={"amount": 50.0, "currency": "USD"})
    assert pay_resp.status_code == 500


def test_complete_verification_consistency_after_rollback(client):
    """Test all read surfaces are mutually consistent after remediation."""
    client.post("/demo/scenarios/bad_deployment/trigger")

    # Execute rollback
    rem_resp = client.post(
        "/internal/remediations",
        json={"action": "rollback_demo_deployment", "parameters": {}}
    )
    assert rem_resp.status_code == 200
    assert rem_resp.json()["status"] == "success"

    # Check 1: Health probe
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["healthy"] is True
    assert health["version"] == "v2.4.0"

    # Check 2: Deployments list
    deployments = client.get("/internal/deployments").json()["items"]
    assert len(deployments) >= 2
    faulty = next(d for d in deployments if d["id"] == "dep_v241_faulty")
    stable = next(d for d in deployments if d["id"] == "dep_v240_stable")
    assert faulty["status"] == "rolled_back"
    assert stable["status"] == "active"
    assert stable["version"] == "v2.4.0"

    # Check 3: Metrics snapshot
    metrics = client.get("/internal/metrics").json()
    assert metrics["is_healthy"] is True
    assert metrics["error_rate_pct"] == 0.0
    assert metrics["scenario"] == "normal"

    # Check 4: Evidence items
    evidence = client.get("/internal/evidence").json()["items"]
    assert len(evidence) >= 3
    state_ev = next(e for e in evidence if e["id"] == "ev_normal_state")
    assert state_ev["details"]["status"] == "UP"

    # Check 5: Scenario list
    scenarios = client.get("/demo/scenarios").json()
    normal_sc = next(s for s in scenarios if s["id"] == "normal")
    assert normal_sc["is_active"] is True
    bad_sc = next(s for s in scenarios if s["id"] == "bad_deployment")
    assert bad_sc["is_active"] is False

    # Check 6: Payments
    pay = client.post("/payments", json={"amount": 100.0, "currency": "USD"}).json()
    assert pay["status"] == "approved"

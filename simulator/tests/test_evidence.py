from datetime import datetime


def test_evidence_structure_and_contract(client):
    """Verify evidence items conform to Section 6 & 8 of api-contract.md."""
    resp = client.get("/internal/evidence")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"items"}, f"Contract requires exactly {{'items'}}, got {set(data.keys())}"
    assert len(data["items"]) > 0

    for item in data["items"]:
        assert "id" in item and isinstance(item["id"], str)
        assert "type" in item and item["type"] in ["log", "metric", "deployment", "state"]
        assert "source" in item and item["source"] == "payment-api"
        assert "timestamp" in item
        # Validate ISO 8601 format
        datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
        assert "summary" in item and isinstance(item["summary"], str)
        assert "details" in item and isinstance(item["details"], dict)


def test_evidence_response_top_level_keys_strict(client):
    """Verify GET /internal/evidence has only 'items' across all scenarios."""
    for sc in ["normal", "database_failure", "payment_timeout", "bad_deployment"]:
        client.post(f"/demo/scenarios/{sc}/trigger")
        resp = client.get("/internal/evidence")
        assert resp.status_code == 200
        keys = set(resp.json().keys())
        assert keys == {"items"}, f"Scenario {sc} returned unexpected keys: {keys}"



def test_database_failure_stable_evidence_ids(client):
    """Verify database_failure produces expected stable evidence IDs for RCA."""
    client.post("/demo/scenarios/database_failure/trigger")
    resp = client.get("/internal/evidence")
    items = resp.json()["items"]
    ids = [item["id"] for item in items]
    
    assert "ev_db_pool_exhausted" in ids
    assert "ev_db_timeout_log" in ids
    assert "ev_db_fatal_log" in ids
    assert "ev_db_state_degraded" in ids


def test_payment_timeout_stable_evidence_ids(client):
    """Verify payment_timeout produces expected stable evidence IDs for RCA."""
    client.post("/demo/scenarios/payment_timeout/trigger")
    resp = client.get("/internal/evidence")
    items = resp.json()["items"]
    ids = [item["id"] for item in items]

    assert "ev_payment_latency_metric" in ids
    assert "ev_gateway_timeout_log" in ids
    assert "ev_deadline_exceeded_log" in ids
    assert "ev_payment_timeout_state" in ids


def test_bad_deployment_stable_evidence_ids(client):
    """Verify bad_deployment produces expected stable evidence IDs for RCA."""
    client.post("/demo/scenarios/bad_deployment/trigger")
    resp = client.get("/internal/evidence")
    items = resp.json()["items"]
    ids = [item["id"] for item in items]

    assert "ev_bad_deploy_event" in ids
    assert "ev_bad_deploy_error_metric" in ids
    assert "ev_bad_deploy_nullpointer_log" in ids
    assert "ev_bad_deploy_state" in ids


def test_evidence_filtering(client):
    """Verify filtering evidence by type and limit."""
    client.post("/demo/scenarios/database_failure/trigger")
    
    # Filter by type=log
    log_resp = client.get("/internal/evidence?type=log")
    log_items = log_resp.json()["items"]
    assert len(log_items) > 0
    for item in log_items:
        assert item["type"] == "log"

    # Filter with limit
    limit_resp = client.get("/internal/evidence?limit=1")
    limit_items = limit_resp.json()["items"]
    assert len(limit_items) == 1

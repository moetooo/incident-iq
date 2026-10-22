def test_payment_success_normal(client):
    """Verify payment succeeds under normal scenario."""
    payload = {
        "amount": 150.0,
        "currency": "USD",
        "payment_method": "credit_card",
        "customer_id": "cust_123"
    }
    resp = client.post("/payments", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["amount"] == 150.0
    assert data["currency"] == "USD"
    assert "tx_" in data["transaction_id"]


def test_payment_failure_database_failure(client):
    """Verify payment returns 503 under database_failure scenario."""
    client.post("/demo/scenarios/database_failure/trigger")
    payload = {"amount": 50.0, "currency": "USD"}
    resp = client.post("/payments", json=payload)
    assert resp.status_code == 503
    data = resp.json()
    assert "error" in data
    assert "Database connection pool exhausted" in data["error"]["message"]


def test_payment_failure_payment_timeout(client):
    """Verify payment returns 504 under payment_timeout scenario."""
    client.post("/demo/scenarios/payment_timeout/trigger")
    payload = {"amount": 50.0, "currency": "USD"}
    resp = client.post("/payments", json=payload)
    assert resp.status_code == 504
    data = resp.json()
    assert "error" in data
    assert "gateway timed out" in data["error"]["message"]


def test_payment_failure_bad_deployment(client):
    """Verify payment returns 500 under bad_deployment scenario."""
    client.post("/demo/scenarios/bad_deployment/trigger")
    payload = {"amount": 50.0, "currency": "USD"}
    resp = client.post("/payments", json=payload)
    assert resp.status_code == 500
    data = resp.json()
    assert "error" in data
    assert "NullPointerException" in data["error"]["message"]


def test_payment_invalid_amount_validation(client):
    """Verify negative amount triggers 422 validation error in standard format."""
    payload = {"amount": -10.0, "currency": "USD"}
    resp = client.post("/payments", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"

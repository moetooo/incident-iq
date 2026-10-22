def test_deployments_baseline(client):
    """Verify default deployments list contains baseline v2.4.0."""
    resp = client.get("/internal/deployments")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    baseline = data["items"][0]
    assert baseline["version"] == "v2.4.0"
    assert baseline["service"] == "payment-api"
    assert baseline["status"] == "active"


def test_deployments_bad_deployment_tracking(client):
    """Verify bad deployment event appears in deployment list upon trigger."""
    client.post("/demo/scenarios/bad_deployment/trigger")
    resp = client.get("/internal/deployments")
    data = resp.json()
    assert len(data["items"]) >= 2
    top = data["items"][0]
    assert top["version"] == "v2.4.1"
    assert top["status"] == "active"
    assert "NullPointer" in top["changelog"] or "token" in top["changelog"].lower()

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


def test_switch_away_from_bad_deployment_marks_faulty_release_rolled_back(client):
    """Verify switching away from bad_deployment marks v2.4.1 as rolled_back and preserves history."""
    # 1. Trigger bad deployment
    client.post("/demo/scenarios/bad_deployment/trigger")
    deps_bad = client.get("/internal/deployments").json()["items"]
    v241_bad = next(d for d in deps_bad if d["version"] == "v2.4.1")
    assert v241_bad["status"] == "active"

    # 2. Transition to database_failure
    client.post("/demo/scenarios/database_failure/trigger")
    deps_db = client.get("/internal/deployments").json()["items"]
    assert len(deps_db) == 2  # history preserved
    v241_db = next(d for d in deps_db if d["version"] == "v2.4.1")
    v240_db = next(d for d in deps_db if d["version"] == "v2.4.0")
    assert v241_db["status"] == "rolled_back", "Faulty release must be marked rolled_back"
    assert v240_db["status"] == "active", "Baseline release must be marked active"

    # 3. Transition to payment_timeout
    client.post("/demo/scenarios/payment_timeout/trigger")
    deps_timeout = client.get("/internal/deployments").json()["items"]
    v241_timeout = next(d for d in deps_timeout if d["version"] == "v2.4.1")
    assert v241_timeout["status"] == "rolled_back"

    # 4. Transition to normal
    client.post("/demo/scenarios/normal/trigger")
    deps_normal = client.get("/internal/deployments").json()["items"]
    assert len(deps_normal) == 2
    v241_normal = next(d for d in deps_normal if d["version"] == "v2.4.1")
    v240_normal = next(d for d in deps_normal if d["version"] == "v2.4.0")
    assert v241_normal["status"] == "rolled_back"
    assert v240_normal["status"] == "active"

    # 5. Reset restores clean factory baseline
    client.post("/demo/scenarios/reset")
    deps_reset = client.get("/internal/deployments").json()["items"]
    assert len(deps_reset) == 1
    assert deps_reset[0]["version"] == "v2.4.0"
    assert deps_reset[0]["status"] == "active"

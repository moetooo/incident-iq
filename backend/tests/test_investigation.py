"""Investigation pipeline tests."""

from __future__ import annotations

from app.investigation.llm.base import LLMProviderError
from app.investigation.llm.schemas import (
    GeneratedHypothesis,
    GeneratedRemediation,
    GeneratedReport,
)
from tests.conftest import FakeProvider, FakeSimulatorClient

DATABASE_EVIDENCE = [
    {
        "type": "log",
        "source": "payment-api",
        "timestamp": "2026-01-01T10:00:00Z",
        "summary": "Database connection timeout: too many connections in the pool",
        "details": {"level": "error"},
    }
]


def _investigate(client, incident_id, scenario_id="database_failure"):
    return client.post(
        f"/api/v1/incidents/{incident_id}/investigate", json={"scenario_id": scenario_id}
    )


def test_investigate_uses_the_deterministic_fallback_without_credentials(
    make_client, incident_payload
):
    simulator = FakeSimulatorClient(evidence=DATABASE_EVIDENCE)
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    response = _investigate(client, incident_id)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["llm_used"] is False
    assert body["provider"] == "deterministic"
    assert body["model"] is None
    assert body["root_cause_hypotheses"], "the fallback must produce a hypothesis"
    assert body["root_cause_hypotheses"][0]["evidence_ids"], "the hypothesis must cite evidence"
    assert body["recommended_checks"]
    assert body["proposed_remediations"]
    assert body["proposed_remediations"][0]["action"] in {
        "rollback_demo_deployment",
        "restart_demo_service",
        "scale_demo_instances",
        "clear_demo_cache",
    }


def test_investigate_uses_the_provider_when_it_is_available(make_client, incident_payload):
    simulator = FakeSimulatorClient(evidence=DATABASE_EVIDENCE)

    def report_factory(request):
        return GeneratedReport(
            summary="The database connection pool was exhausted.",
            root_cause_hypotheses=[
                GeneratedHypothesis(
                    cause="Database connection pool exhaustion",
                    explanation="The pool reported saturation in the collected logs.",
                    confidence=0.82,
                    evidence_ids=[request.evidence[0].id],
                    recommended_action_type="restart_demo_service",
                )
            ],
            recommended_checks=["Inspect the pool configuration."],
            proposed_remediations=[
                GeneratedRemediation(
                    action="restart_demo_service",
                    parameters={},
                    risk_level="medium",
                    rationale="A restart releases the saturated pool.",
                )
            ],
        )

    provider = FakeProvider(report=report_factory)
    client = make_client(simulator, provider_factory=lambda: provider)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    response = _investigate(client, incident_id)

    assert response.status_code == 200
    body = response.json()
    assert body["llm_used"] is True
    assert body["provider"] == "gemini"
    assert body["model"] == "gemini-test-model"
    assert body["root_cause_hypotheses"][0]["confidence"] == 0.82
    assert body["root_cause_hypotheses"][0]["evidence_ids"] == [provider.requests[0].evidence[0].id]
    assert body["proposed_remediations"][0]["action"] == "restart_demo_service"


def test_investigate_discards_hypotheses_that_cite_unknown_evidence(make_client, incident_payload):
    simulator = FakeSimulatorClient(evidence=DATABASE_EVIDENCE)

    def report_factory(request):
        return GeneratedReport(
            summary="A fabricated answer.",
            root_cause_hypotheses=[
                GeneratedHypothesis(
                    cause="Fabricated cause",
                    explanation="Cited evidence ev_ffffffffffff.",
                    confidence=0.99,
                    evidence_ids=["ev_ffffffffffff"],
                )
            ],
        )

    provider = FakeProvider(report=report_factory)
    client = make_client(simulator, provider_factory=lambda: provider)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    response = _investigate(client, incident_id)

    assert response.status_code == 200
    body = response.json()
    assert body["llm_used"] is False, "an unverifiable report must fall back"
    assert body["provider"] == "deterministic"
    assert any("unknown evidence" in warning for warning in body["warnings"])
    assert all(
        hypothesis["cause"] != "Fabricated cause" for hypothesis in body["root_cause_hypotheses"]
    )


def test_investigate_falls_back_when_the_provider_fails(make_client, incident_payload):
    simulator = FakeSimulatorClient(evidence=DATABASE_EVIDENCE)
    provider = FakeProvider(error=LLMProviderError("provider timed out", reason="timeout"))
    client = make_client(simulator, provider_factory=lambda: provider)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    response = _investigate(client, incident_id)

    assert response.status_code == 200
    body = response.json()
    assert body["llm_used"] is False
    assert body["provider"] == "deterministic"
    assert any("timeout" in warning for warning in body["warnings"])
    assert body["root_cause_hypotheses"]


def test_investigate_survives_an_unreachable_simulator(make_client, incident_payload):
    simulator = FakeSimulatorClient(unavailable=True)
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    response = _investigate(client, incident_id)

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_ids"] == []
    assert body["warnings"]
    assert body["llm_used"] is False


def test_investigate_creates_a_pending_remediation_proposal(make_client, incident_payload):
    simulator = FakeSimulatorClient(evidence=DATABASE_EVIDENCE)
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    report = _investigate(client, incident_id).json()

    remediations = client.get(f"/api/v1/incidents/{incident_id}/remediations").json()
    assert remediations["total"] >= 1
    assert remediations["items"][0]["status"] == "pending_approval"
    assert remediations["items"][0]["requires_human_approval"] is True

    incident = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert incident["status"] == "awaiting_approval"
    assert report["proposed_remediations"]


def test_investigation_report_can_be_read_back(make_client, incident_payload):
    simulator = FakeSimulatorClient(evidence=DATABASE_EVIDENCE)
    client = make_client(simulator)
    incident_id = client.post("/api/v1/incidents", json=incident_payload).json()["id"]

    created = _investigate(client, incident_id).json()

    response = client.get(
        f"/api/v1/incidents/{incident_id}/investigations/{created['id']}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["summary"] == created["summary"]
    assert body["root_cause_hypotheses"][0]["id"] == created["root_cause_hypotheses"][0]["id"]
    assert body["evidence_ids"] == created["evidence_ids"]

    listed = client.get(f"/api/v1/incidents/{incident_id}/investigations").json()
    assert listed["total"] == 1


def test_investigate_returns_404_for_an_unknown_incident(client):
    response = client.post("/api/v1/incidents/inc_missing/investigate", json={})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INCIDENT_NOT_FOUND"

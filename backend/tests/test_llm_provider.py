"""Unit tests for the Gemini analysis provider.

The provider SDK is mocked: no test performs a network call.
"""

from __future__ import annotations

import json

import httpx
import pytest
from google.genai import errors as genai_errors

from app.investigation.llm.base import AnalysisRequest, EvidenceItem, LLMProviderError
from app.investigation.llm.gemini_provider import GeminiProvider
from app.investigation.llm.schemas import gemini_response_schema

VALID_PAYLOAD = {
    "summary": "The pool was exhausted.",
    "root_cause_hypotheses": [
        {
            "cause": "Database connection pool exhaustion",
            "explanation": "The logs show pool saturation.",
            "confidence": 0.8,
            "evidence_ids": ["ev_aaaaaaaaaaaa"],
            "recommended_action_type": "restart_demo_service",
        }
    ],
    "alternative_hypotheses": [],
    "recommended_checks": ["Inspect the pool size."],
    "proposed_remediations": [
        {
            "action": "restart_demo_service",
            "parameters": {},
            "risk_level": "medium",
            "rationale": "A restart releases the pool.",
        }
    ],
}


def _request() -> AnalysisRequest:
    return AnalysisRequest(
        incident_id="inc_test",
        title="Payment API timeouts",
        service="payment-api",
        severity="high",
        description="Requests are timing out",
        evidence=[
            EvidenceItem(
                id="ev_aaaaaaaaaaaa",
                type="log",
                source="payment-api",
                timestamp="2026-01-01T10:00:00+00:00",
                summary="Database connection timeout",
                details={"level": "error"},
                confidence=0.9,
            )
        ],
    )


class _FakeModels:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


class _FakeClient:
    def __init__(self, models: _FakeModels) -> None:
        self.models = models


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


@pytest.fixture
def fake_client(monkeypatch):
    """Install a fake google-genai client and return the created fake."""
    from google import genai

    holder: dict[str, _FakeClient] = {}

    def _install(models: _FakeModels) -> _FakeClient:
        client = _FakeClient(models)
        holder["client"] = client
        monkeypatch.setattr(genai, "Client", lambda **kwargs: client)
        return client

    return _install


def test_provider_returns_a_validated_report(fake_client):
    models = _FakeModels(_FakeResponse(json.dumps(VALID_PAYLOAD)))
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")
    report = provider.analyze(_request())

    assert report.summary == "The pool was exhausted."
    assert report.root_cause_hypotheses[0].cause == "Database connection pool exhaustion"
    assert report.root_cause_hypotheses[0].evidence_ids == ["ev_aaaaaaaaaaaa"]
    assert report.proposed_remediations[0].action == "restart_demo_service"


def test_provider_sends_structured_output_configuration(fake_client):
    models = _FakeModels(_FakeResponse(json.dumps(VALID_PAYLOAD)))
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")
    provider.analyze(_request())

    call = models.calls[0]
    assert call["model"] == "gemini-3.5-flash-lite"
    assert call["config"]["response_mime_type"] == "application/json"
    assert call["config"]["response_json_schema"]["type"] == "object"
    prompt = call["contents"]
    assert "ev_aaaaaaaaaaaa" in prompt
    assert "restart_demo_service" in prompt


def test_provider_rejects_malformed_json(fake_client):
    models = _FakeModels(_FakeResponse("not json at all"))
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "malformed_output"


def test_provider_rejects_an_empty_response(fake_client):
    models = _FakeModels(_FakeResponse(""))
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "malformed_output"


def test_provider_rejects_output_that_fails_validation(fake_client):
    payload = dict(VALID_PAYLOAD)
    payload["root_cause_hypotheses"] = [{"cause": "", "confidence": 0.5}]
    models = _FakeModels(_FakeResponse(json.dumps(payload)))
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "validation_error"


def test_provider_classifies_a_rate_limit(fake_client):
    error = genai_errors.ClientError(code=429, response_json={"error": {"code": 429}})
    models = _FakeModels(error=error)
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "rate_limited"


def test_provider_classifies_a_service_unavailable(fake_client):
    error = genai_errors.APIError(code=503, response_json={"error": {"code": 503}})
    models = _FakeModels(error=error)
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "unavailable"


def test_provider_classifies_a_timeout(fake_client):
    models = _FakeModels(error=httpx.TimeoutException("request timed out"))
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "timeout"


def test_provider_reports_missing_credentials():
    provider = GeminiProvider(api_key=None, model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "missing_credentials"


def test_provider_classifies_an_auth_error_as_config_error(fake_client):
    error = genai_errors.ClientError(code=401, response_json={"error": {"code": 401}})
    models = _FakeModels(error=error)
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "config_error"


def test_provider_classifies_a_forbidden_error_as_config_error(fake_client):
    error = genai_errors.ClientError(code=403, response_json={"error": {"code": 403}})
    models = _FakeModels(error=error)
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "config_error"


def test_provider_rejects_zero_hypotheses_with_evidence(fake_client):
    payload = dict(VALID_PAYLOAD)
    payload["root_cause_hypotheses"] = []
    models = _FakeModels(_FakeResponse(json.dumps(payload)))
    fake_client(models)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.5-flash-lite")

    with pytest.raises(LLMProviderError) as excinfo:
        provider.analyze(_request())

    assert excinfo.value.reason == "no_usable_hypotheses"


def test_response_schema_is_flat():
    schema = gemini_response_schema()

    assert "$ref" not in json.dumps(schema)
    assert "$defs" not in schema
    assert set(schema["required"]) == {
        "summary",
        "root_cause_hypotheses",
        "alternative_hypotheses",
        "recommended_checks",
        "proposed_remediations",
    }

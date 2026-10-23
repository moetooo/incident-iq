"""Tests for the Gemini fallback orchestrator."""

from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.investigation.deterministic import DeterministicEngine
from app.investigation.llm.base import (
    AnalysisRequest,
    EvidenceItem,
    LLMProviderError,
)
from app.investigation.llm.model_discovery import DiscoveredModel
from app.investigation.llm.model_fallback import (
    GeminiFallbackOrchestrator,
)


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


def _discovered(model_id: str, structured: bool = True) -> DiscoveredModel:
    return DiscoveredModel(
        model_id=model_id,
        display_name=model_id,
        description=None,
        supports_structured_output=structured,
        free_tier_eligible=None,
        input_token_limit=None,
        output_token_limit=None,
    )


class _FakeDiscovery:
    def __init__(self, candidates: list[DiscoveredModel]) -> None:
        self._candidates = candidates

    def get_eligible_models(self) -> list[DiscoveredModel]:
        return self._candidates

    def get_fallback_candidates(
        self, primary_model: str, max_candidates: int | None = None
    ) -> list[DiscoveredModel]:
        return self._candidates


class _FakeProvider:
    def __init__(self, model: str, report=None, error=None) -> None:
        self.model = model
        self.report = report
        self.error = error
        self.calls: list = []

    def analyze(self, request):
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.report


def _settings(**overrides) -> Settings:
    base = dict(
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="gemini-3.5-flash-lite",
        GEMINI_MAX_FALLBACK_ATTEMPTS=3,
        GEMINI_FALLBACK_TIME_BUDGET_SECONDS=30.0,
        LLM_TIMEOUT_SECONDS=45.0,
        LLM_ENABLED=True,
    )
    base.update(overrides)
    return Settings(**base)


def _run(analyze_coro):
    return asyncio.run(analyze_coro)


def test_primary_succeeds_returns_report():
    report = DeterministicEngine().analyze(_request())

    def factory(model):
        return _FakeProvider(model, report=report)

    settings = _settings()
    orchestrator = GeminiFallbackOrchestrator(
        settings=settings,
        discovery_service=_FakeDiscovery([]),
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )
    orchestrator._create_provider = factory  # noqa: SLF001

    result = _run(orchestrator.analyze(_request(), settings.GEMINI_MODEL))

    assert result.llm_used is True
    assert result.provider_name == "gemini"
    assert result.model == settings.GEMINI_MODEL
    assert result.fallback_used is False
    assert len(result.attempts) == 1
    assert result.attempts[0].success is True


def test_falls_back_to_secondary_on_retryable_error():
    secondary_report = DeterministicEngine().analyze(_request())

    def factory(model):
        if model == "gemini-3.5-flash-lite":
            return _FakeProvider(
                model,
                error=LLMProviderError("limited", reason="rate_limited"),
            )
        return _FakeProvider(model, report=secondary_report)

    settings = _settings(GEMINI_MAX_FALLBACK_ATTEMPTS=3)
    discovery = _FakeDiscovery([_discovered("gemini-2.0-flash")])
    orchestrator = GeminiFallbackOrchestrator(
        settings=settings,
        discovery_service=discovery,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )
    orchestrator._create_provider = factory  # noqa: SLF001

    result = _run(orchestrator.analyze(_request(), settings.GEMINI_MODEL))

    assert result.llm_used is True
    assert result.provider_name == "gemini"
    assert result.model == "gemini-2.0-flash"
    assert result.fallback_used is True
    assert len(result.attempts) == 2
    assert result.attempts[0].success is False
    assert result.attempts[0].reason == "rate_limited"
    assert result.attempts[1].success is True


def test_config_error_aborts_without_retry():
    def factory(model):
        return _FakeProvider(
            model,
            error=LLMProviderError("bad key", reason="config_error"),
        )

    settings = _settings(GEMINI_MAX_FALLBACK_ATTEMPTS=3)
    discovery = _FakeDiscovery([_discovered("gemini-2.0-flash")])
    orchestrator = GeminiFallbackOrchestrator(
        settings=settings,
        discovery_service=discovery,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )
    orchestrator._create_provider = factory  # noqa: SLF001

    result = _run(orchestrator.analyze(_request(), settings.GEMINI_MODEL))

    assert result.llm_used is False
    assert result.provider_name == DeterministicEngine().name
    assert result.model is None
    assert result.fallback_used is True
    assert len(result.attempts) == 1  # config errors are not retried
    assert result.attempts[0].reason == "config_error"


def test_all_fail_uses_deterministic_fallback():
    def factory(model):
        return _FakeProvider(
            model,
            error=LLMProviderError("down", reason="unavailable"),
        )

    settings = _settings(GEMINI_MAX_FALLBACK_ATTEMPTS=2)
    discovery = _FakeDiscovery([_discovered("gemini-2.0-flash")])
    orchestrator = GeminiFallbackOrchestrator(
        settings=settings,
        discovery_service=discovery,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )
    orchestrator._create_provider = factory  # noqa: SLF001

    result = _run(orchestrator.analyze(_request(), settings.GEMINI_MODEL))

    assert result.llm_used is False
    assert result.provider_name == DeterministicEngine().name
    assert result.model is None
    assert result.fallback_used is True
    assert len(result.attempts) == 2
    assert all(a.success is False for a in result.attempts)

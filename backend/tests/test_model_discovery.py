"""Tests for dynamic Gemini model discovery."""

from __future__ import annotations

from types import SimpleNamespace

from app.core.config import Settings
from app.investigation.llm.model_discovery import (
    ModelDiscoveryService,
    create_model_discovery_service,
)


def _make_model(
    name: str,
    supported_actions: tuple[str, ...] = ("generateContent",),
    labels: dict | None = None,
    **attrs,
) -> SimpleNamespace:
    model = SimpleNamespace(
        name=name,
        display_name=name,
        description="",
        supported_actions=list(supported_actions),
        labels=labels or {},
        input_token_limit=None,
        output_token_limit=None,
    )
    for key, value in attrs.items():
        setattr(model, key, value)
    return model


class _FakePager:
    def __init__(self, models: list) -> None:
        self._models = models

    def __iter__(self):
        return iter(self._models)


class _FakeModels:
    def __init__(self, models: list) -> None:
        self.models = models

    def list(self, config=None) -> _FakePager:
        return _FakePager(self.models)


class _FakeClient:
    def __init__(self, models: list) -> None:
        self.models = _FakeModels(models)


def _install_client(monkeypatch, models: list) -> None:
    from google import genai

    monkeypatch.setattr(genai, "Client", lambda **kwargs: _FakeClient(models))


def test_discovery_filters_for_generate_content(monkeypatch):
    models = [
        _make_model("models/gemini-1.5-flash", supported_actions=("generateContent",)),
        _make_model(
            "models/gemini-embedding-001",
            supported_actions=("embedContent",),
        ),
    ]
    _install_client(monkeypatch, models)

    service = ModelDiscoveryService(api_key="test-key")
    discovered = service.get_eligible_models()

    assert len(discovered) == 1
    assert discovered[0].model_id == "gemini-1.5-flash"


def test_structured_output_inference(monkeypatch):
    models = [
        _make_model("models/gemini-1.5-pro"),
        _make_model("models/gemini-2.0-flash"),
        _make_model("models/gemini-1.0-pro"),
    ]
    _install_client(monkeypatch, models)

    service = ModelDiscoveryService(api_key="test-key")
    discovered = service.get_eligible_models()

    by_id = {m.model_id: m for m in discovered}
    assert by_id["gemini-1.5-pro"].supports_structured_output is True
    assert by_id["gemini-2.0-flash"].supports_structured_output is True
    assert by_id["gemini-1.0-pro"].supports_structured_output is False


def test_free_tier_inference(monkeypatch):
    models = [
        _make_model("models/gemini-1.5-flash"),
        _make_model("models/gemini-2.0-pro"),
    ]
    _install_client(monkeypatch, models)

    service = ModelDiscoveryService(api_key="test-key")
    discovered = service.get_eligible_models()

    by_id = {m.model_id: m for m in discovered}
    assert by_id["gemini-1.5-flash"].free_tier_eligible is True
    assert by_id["gemini-2.0-pro"].free_tier_eligible is None


def test_fallback_candidates_exclude_primary(monkeypatch):
    models = [
        _make_model("models/gemini-1.5-flash"),
        _make_model("models/gemini-2.0-flash"),
        _make_model("models/gemini-1.5-pro"),
    ]
    _install_client(monkeypatch, models)

    service = ModelDiscoveryService(api_key="test-key")
    candidates = service.get_fallback_candidates("gemini-1.5-flash")

    ids = [c.model_id for c in candidates]
    assert "gemini-1.5-flash" not in ids


def test_fallback_candidates_prefer_structured_output(monkeypatch):
    models = [
        _make_model("models/gemini-embedding-001", supported_actions=("embedContent",)),
        _make_model("models/gemini-2.0-flash", supported_actions=("generateContent",)),
        _make_model("models/gemini-1.0-pro", supported_actions=("generateContent",)),
    ]
    _install_client(monkeypatch, models)

    service = ModelDiscoveryService(api_key="test-key")
    candidates = service.get_fallback_candidates("gemini-1.5-flash")

    assert candidates[0].supports_structured_output is True
    assert candidates[0].model_id == "gemini-2.0-flash"


def test_create_service_returns_none_without_api_key():
    settings = Settings(GEMINI_API_KEY=None)
    assert create_model_discovery_service(settings) is None


def test_create_service_returns_service_with_api_key():
    settings = Settings(GEMINI_API_KEY="test-key")
    service = create_model_discovery_service(settings)
    assert isinstance(service, ModelDiscoveryService)
    assert service._cache_ttl_seconds == settings.GEMINI_MODEL_DISCOVERY_TTL_SECONDS


def test_cached_models_returned_without_refetch(monkeypatch):
    calls = []

    class _CountingClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        class models:
            @staticmethod
            def list(config=None):
                return _FakePager([])

    from google import genai

    monkeypatch.setattr(genai, "Client", _CountingClient)

    service = ModelDiscoveryService(api_key="test-key", cache_ttl_seconds=3600)
    service.get_eligible_models()
    service.get_eligible_models()

    assert len(calls) == 1

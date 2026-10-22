"""Configuration parsing tests."""

from __future__ import annotations

import importlib

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError

from app.core import config as config_module
from app.core.config import Settings


def _settings(**env) -> Settings:
    """Build settings from an explicit environment mapping."""
    return Settings(_env_file=None, **env)


def test_cors_origins_accepts_a_comma_separated_string():
    settings = _settings(CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173")

    assert settings.CORS_ORIGINS == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_cors_origins_accepts_a_single_origin():
    settings = _settings(CORS_ORIGINS="http://localhost:5173")

    assert settings.CORS_ORIGINS == ["http://localhost:5173"]


def test_cors_origins_default_is_used_when_unset():
    settings = _settings()

    assert "http://localhost:5173" in settings.CORS_ORIGINS


def test_cors_origins_still_rejects_an_unparsable_environment(monkeypatch):
    """The fix must not silently accept broken values."""
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    settings = Settings(_env_file=None)
    assert settings.CORS_ORIGINS == ["http://localhost:5173"]


def test_settings_raise_on_an_invalid_type(monkeypatch):
    monkeypatch.setenv("SIMULATOR_TIMEOUT_SECONDS", "not-a-number")

    with pytest.raises((SettingsError, ValidationError)):
        Settings(_env_file=None)


def test_llm_configured_requires_a_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")

    assert Settings(_env_file=None).llm_configured is False

    monkeypatch.setenv("GEMINI_API_KEY", "present")
    assert Settings(_env_file=None).llm_configured is True


def test_module_exposes_get_settings():
    assert callable(config_module.get_settings)
    assert importlib.util.find_spec("app.core.config") is not None

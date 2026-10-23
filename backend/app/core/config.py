"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Every value can be overridden with an environment variable of the same
    name. The backend must start and remain healthy without an LLM API key.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "IncidentIQ Backend"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"

    # Authentication. API_KEY is optional; when unset the API runs in local
    # demo mode without service authentication.
    API_KEY: str | None = None

    # ``NoDecode`` stops pydantic-settings from JSON-decoding the environment
    # value. Without it a comma separated value such as
    # "http://localhost:5173,http://127.0.0.1:5173" fails to parse as JSON
    # and the application fails to start.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Database
    DATABASE_URL: str = "postgresql+psycopg://incidentiq:incidentiq@db:5432/incidentiq"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 5

    # Simulator
    SIMULATOR_BASE_URL: str = "http://simulator:8001"
    SIMULATOR_TIMEOUT_SECONDS: float = 10.0

    # LLM provider
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    LLM_ENABLED: bool = True
    LLM_TIMEOUT_SECONDS: float = 45.0
    LLM_MAX_EVIDENCE_ITEMS: int = 40

    # Gemini model discovery and fallback
    GEMINI_MODEL_DISCOVERY_TTL_SECONDS: int = 3600
    GEMINI_MAX_FALLBACK_ATTEMPTS: int = 3
    GEMINI_FALLBACK_TIME_BUDGET_SECONDS: float = 30.0

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        """Accept a comma-separated string for CORS_ORIGINS."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def llm_configured(self) -> bool:
        """True when a provider call could be attempted."""
        return bool(self.LLM_ENABLED and self.GEMINI_API_KEY)

    @property
    def auth_required(self) -> bool:
        """True when requests must carry a valid ``X-API-Key`` header."""
        return bool(self.API_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()

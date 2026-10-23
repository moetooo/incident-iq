"""Dynamic Gemini model discovery service.

Discovers available models at runtime using the Google Generative AI API,
caches the results, and filters for models suitable for text-based RCA
investigations with structured output support.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DiscoveredModel:
    """A discovered Gemini model with metadata."""

    model_id: str
    display_name: str
    description: str | None
    supports_structured_output: bool
    free_tier_eligible: bool | None
    input_token_limit: int | None
    output_token_limit: int | None


class ModelDiscoveryService:
    """Discovers and caches available Gemini models."""

    def __init__(
        self,
        *,
        api_key: str,
        cache_ttl_seconds: int = 3600,
        max_models_per_page: int = 100,
    ) -> None:
        self._api_key = api_key
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_models_per_page = max_models_per_page
        self._cached_models: list[DiscoveredModel] | None = None
        self._cache_timestamp: float | None = None

    def _is_cache_valid(self) -> bool:
        if self._cached_models is None or self._cache_timestamp is None:
            return False
        return (time.monotonic() - self._cache_timestamp) < self._cache_ttl_seconds

    def _extract_model_id(self, name: str) -> str:
        """Extract the short model ID from the full resource name.

        e.g. "models/gemini-1.5-flash" -> "gemini-1.5-flash"
        """
        if name.startswith("models/"):
            return name[len("models/"):]
        return name

    def _model_supports_text_generation(self, model: Any) -> bool:
        """Check if model supports text generation (generateContent)."""
        supported_actions = getattr(model, "supported_actions", None)
        if not supported_actions:
            return False
        # Look for text generation capability
        actions = [a.lower() for a in supported_actions]
        return any("generatecontent" in a for a in actions)

    def _model_supports_structured_output(self, model: Any) -> bool:
        """Check if model likely supports structured JSON output.

        Models that support generateContent with JSON response mime type
        are assumed to support structured output. We can't definitively
        know from the API metadata, so we rely on generateContent support
        and known model families.
        """
        if not self._model_supports_text_generation(model):
            return False
        # Prefer models known to support response_json_schema
        model_id = self._extract_model_id(getattr(model, "name", "")).lower()
        # Known structured-output capable families
        structured_families = (
            "gemini-1.5",
            "gemini-2.0",
            "gemini-2.5",
            "gemini-3.5",
        )
        return any(family in model_id for family in structured_families)

    def _is_free_tier_eligible(self, model: Any) -> bool | None:
        """Determine if model is likely free-tier eligible.

        Google's API does not expose pricing/free-tier metadata reliably.
        We infer from labels and known free models. Returns None when
        eligibility cannot be determined.
        """
        labels = getattr(model, "labels", None) or {}
        label_text = " ".join(
            f"{k}={v}" for k, v in labels.items()
        ).lower()

        # Known free-tier indicators (heuristic)
        if "free" in label_text or "tier" in label_text:
            return True

        model_id = self._extract_model_id(getattr(model, "name", "")).lower()
        # Known free models (as of current API)
        known_free = (
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-3.5-flash-lite",
        )
        if model_id in known_free:
            return True

        # Can't determine
        return None

    def _fetch_models(self) -> list[DiscoveredModel]:
        """Fetch and filter models from the Gemini API."""
        try:
            from google import genai
        except ImportError as exc:
            logger.warning(
                "gemini_model_discovery_failed",
                extra={"reason": f"google-genai not available: {exc}"},
            )
            return []

        try:
            client = genai.Client(api_key=self._api_key)
        except Exception as exc:
            logger.warning(
                "gemini_model_discovery_failed",
                extra={"reason": f"client init failed: {exc}"},
            )
            return []

        models: list[DiscoveredModel] = []
        page_size = self._max_models_per_page

        try:
            # The Pager handles pagination automatically when iterated
            pager = client.models.list(config={"page_size": page_size})
            for model in pager:
                model_id = self._extract_model_id(getattr(model, "name", ""))
                if not model_id:
                    continue

                supports_structured = self._model_supports_structured_output(model)
                free_eligible = self._is_free_tier_eligible(model)

                # Only include models that support text generation
                if not self._model_supports_text_generation(model):
                    continue

                discovered = DiscoveredModel(
                    model_id=model_id,
                    display_name=getattr(model, "display_name", None) or model_id,
                    description=getattr(model, "description", None),
                    supports_structured_output=supports_structured,
                    free_tier_eligible=free_eligible,
                    input_token_limit=getattr(model, "input_token_limit", None),
                    output_token_limit=getattr(model, "output_token_limit", None),
                )
                models.append(discovered)

            logger.info(
                "gemini_models_discovered",
                extra={
                    "count": len(models),
                    "structured_output_capable": sum(
                        1 for m in models if m.supports_structured_output
                    ),
                    "free_tier_known": sum(
                        1 for m in models if m.free_tier_eligible is True
                    ),
                },
            )
            return models

        except Exception as exc:
            logger.warning(
                "gemini_model_discovery_failed",
                extra={"reason": str(exc)},
            )
            return []

    def get_eligible_models(self) -> list[DiscoveredModel]:
        """Return cached models, refreshing if stale."""
        if self._is_cache_valid():
            return self._cached_models

        models = self._fetch_models()
        self._cached_models = models
        self._cache_timestamp = time.monotonic()
        return models

    def get_fallback_candidates(
        self, primary_model: str, max_candidates: int | None = None
    ) -> list[DiscoveredModel]:
        """Return fallback model candidates excluding the primary model.

        Prefers models that:
        1. Support structured output
        2. Are free-tier eligible (or unknown)
        3. Are not the primary model
        """
        models = self.get_eligible_models()

        candidates = [
            m for m in models
            if m.model_id != primary_model
        ]

        # Sort: structured output first, then free-tier eligible, then by name
        candidates.sort(
            key=lambda m: (
                not m.supports_structured_output,
                m.free_tier_eligible is not True,  # True first, then None, then False
                m.model_id,
            )
        )

        if max_candidates:
            candidates = candidates[:max_candidates]

        return candidates


def create_model_discovery_service(settings: Settings) -> ModelDiscoveryService | None:
    """Create a ModelDiscoveryService if an API key is configured."""
    if not settings.GEMINI_API_KEY:
        return None
    return ModelDiscoveryService(
        api_key=settings.GEMINI_API_KEY,
        cache_ttl_seconds=settings.GEMINI_MODEL_DISCOVERY_TTL_SECONDS,
    )
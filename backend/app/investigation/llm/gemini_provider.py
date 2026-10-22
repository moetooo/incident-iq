"""Gemini implementation of the incident analysis provider.

The provider talks to the official Gemini API through the ``google-genai``
SDK. It is used by the backend only; the API key never leaves the server.
"""

from __future__ import annotations

import json

from app.core.logging import get_logger
from app.investigation.llm.base import AnalysisRequest, LLMProvider, LLMProviderError
from app.investigation.llm.prompts import build_prompt
from app.investigation.llm.schemas import GeneratedReport, gemini_response_schema

logger = get_logger(__name__)


class GeminiProvider(LLMProvider):
    """Structured RCA generation backed by the Gemini API."""

    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 45.0,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._client = None

    def _get_client(self):
        """Create the SDK client lazily so the app starts without credentials."""
        if self._client is not None:
            return self._client

        if not self._api_key:
            raise LLMProviderError(
                "GEMINI_API_KEY is not configured", reason="missing_credentials"
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise LLMProviderError(
                f"The google-genai package is not available: {exc}", reason="missing_dependency"
            ) from exc

        try:
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=int(self._timeout_seconds * 1000)),
            )
        except Exception as exc:  # pragma: no cover - provider guard
            raise LLMProviderError(
                f"Could not initialise the Gemini client: {exc}", reason="provider_error"
            ) from exc

        return self._client

    def analyze(self, request: AnalysisRequest) -> GeneratedReport:
        """Return a structured RCA report for the incident."""
        client = self._get_client()
        prompt = build_prompt(request)

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": gemini_response_schema(),
                },
            )
        except Exception as exc:
            raise self._classify(exc) from exc

        text = getattr(response, "text", None)
        if not text:
            raise LLMProviderError(
                "The Gemini API returned an empty response", reason="malformed_output"
            )

        try:
            payload = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise LLMProviderError(
                f"The Gemini API returned invalid JSON: {exc}", reason="malformed_output"
            ) from exc

        if not isinstance(payload, dict):
            raise LLMProviderError(
                "The Gemini API returned a JSON value that is not an object",
                reason="malformed_output",
            )

        try:
            report = GeneratedReport.model_validate(payload)
        except Exception as exc:
            raise LLMProviderError(
                f"The Gemini API response failed validation: {exc}", reason="validation_error"
            ) from exc

        logger.info(
            "gemini_analysis_completed",
            extra={"model": self.model, "hypotheses": len(report.root_cause_hypotheses)},
        )
        return report

    @staticmethod
    def _classify(exc: Exception) -> LLMProviderError:
        """Map a provider exception onto a typed error with a stable reason."""
        message = str(exc) or exc.__class__.__name__

        try:
            import httpx
            from google.genai import errors as genai_errors
        except ImportError:  # pragma: no cover - dependency guard
            return LLMProviderError(message, reason="provider_error")

        if isinstance(exc, httpx.TimeoutException):
            return LLMProviderError(message, reason="timeout")
        if isinstance(exc, genai_errors.ClientError):
            code = getattr(exc, "code", None)
            if code == 429:
                return LLMProviderError(message, reason="rate_limited")
            return LLMProviderError(message, reason="provider_error")
        if isinstance(exc, genai_errors.APIError):
            return LLMProviderError(message, reason="provider_error")
        if "timeout" in message.lower():
            return LLMProviderError(message, reason="timeout")
        return LLMProviderError(message, reason="provider_error")

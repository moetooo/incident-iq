"""Gemini implementation of the incident analysis provider.

The provider talks to the official Gemini API through the ``google-genai``
SDK. It is used by the backend only; the API key never leaves the server.
"""

from __future__ import annotations

import json
import time

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

        logger.info(
            "gemini_provider_initialized",
            extra={"model": self.model},
        )

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
        """Return a structured RCA report for the incident.

        A successful HTTP response is not enough: the response must produce a
        valid report with at least one root-cause hypothesis when evidence was
        provided. An empty hypothesis list is treated as a soft failure so the
        caller can try another eligible Gemini model.
        """
        start = time.monotonic()
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
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "gemini_model_attempt_failed",
                extra={
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "reason": self._classify(exc).reason,
                },
            )
            raise self._classify(exc) from exc

        text = getattr(response, "text", None)
        if not text:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "gemini_model_attempt_failed",
                extra={
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "reason": "malformed_output",
                },
            )
            raise LLMProviderError(
                "The Gemini API returned an empty response", reason="malformed_output"
            )

        try:
            payload = json.loads(text)
        except (TypeError, ValueError) as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "gemini_model_attempt_failed",
                extra={
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "reason": "malformed_output",
                },
            )
            raise LLMProviderError(
                f"The Gemini API returned invalid JSON: {exc}", reason="malformed_output"
            ) from exc

        if not isinstance(payload, dict):
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "gemini_model_attempt_failed",
                extra={
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "reason": "malformed_output",
                },
            )
            raise LLMProviderError(
                "The Gemini API returned a JSON value that is not an object",
                reason="malformed_output",
            )

        try:
            report = GeneratedReport.model_validate(payload)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "gemini_model_attempt_failed",
                extra={
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "reason": "validation_error",
                },
            )
            raise LLMProviderError(
                f"The Gemini API response failed validation: {exc}", reason="validation_error"
            ) from exc

        if not report.root_cause_hypotheses and request.evidence:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "gemini_model_attempt_failed",
                extra={
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "reason": "no_usable_hypotheses",
                },
            )
            raise LLMProviderError(
                "The Gemini API returned a valid response with no root-cause hypotheses",
                reason="no_usable_hypotheses",
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "gemini_analysis_completed",
            extra={
                "model": self.model,
                "hypotheses": len(report.root_cause_hypotheses),
                "duration_ms": duration_ms,
            },
        )
        return report

    def _classify(self, exc: Exception) -> LLMProviderError:
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
                logger.warning(
                    "gemini_rate_limited",
                    extra={"model": self.model},
                )
                return LLMProviderError(message, reason="rate_limited")
            if code in (401, 403):
                logger.warning(
                    "gemini_auth_error",
                    extra={"model": self.model},
                )
                return LLMProviderError(message, reason="config_error")
            if code == 404:
                logger.warning(
                    "gemini_model_not_found",
                    extra={"model": self.model},
                )
                return LLMProviderError(message, reason="model_not_found")
            if code == 503 or (500 <= code < 600):
                logger.warning(
                    "gemini_unavailable",
                    extra={"model": self.model},
                )
                return LLMProviderError(message, reason="unavailable")
            return LLMProviderError(message, reason="provider_error")
        if isinstance(exc, genai_errors.APIError):
            code = getattr(exc, "code", None)
            if code == 429:
                logger.warning(
                    "gemini_rate_limited",
                    extra={"model": self.model},
                )
                return LLMProviderError(message, reason="rate_limited")
            if code in (401, 403):
                logger.warning(
                    "gemini_auth_error",
                    extra={"model": self.model},
                )
                return LLMProviderError(message, reason="config_error")
            if code == 404:
                logger.warning(
                    "gemini_model_not_found",
                    extra={"model": self.model},
                )
                return LLMProviderError(message, reason="model_not_found")
            if code == 503 or (500 <= code < 600):
                logger.warning(
                    "gemini_unavailable",
                    extra={"model": self.model},
                )
                return LLMProviderError(message, reason="unavailable")
            return LLMProviderError(message, reason="provider_error")
        if "timeout" in message.lower():
            return LLMProviderError(message, reason="timeout")
        return LLMProviderError(message, reason="provider_error")

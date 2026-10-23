"""Gemini model fallback orchestrator.

Coordinates attempts across multiple discovered Gemini models with bounded
attempts and time budget. Falls back to deterministic engine when all
eligible models fail.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.core.config import Settings
from app.core.logging import get_logger
from app.investigation.deterministic import DeterministicEngine
from app.investigation.llm.base import (
    AnalysisRequest,
    GeneratedReport,
    LLMProviderError,
)
from app.investigation.llm.gemini_provider import GeminiProvider
from app.investigation.llm.model_discovery import ModelDiscoveryService

logger = get_logger(__name__)


@dataclass(frozen=True)
class FallbackResult:
    """Result of the fallback sequence."""

    report: GeneratedReport
    provider_name: str
    model: str | None
    llm_used: bool
    attempts: list[AttemptRecord]
    fallback_used: bool


@dataclass(frozen=True)
class AttemptRecord:
    """Record of a single model attempt."""

    model: str
    attempt_number: int
    duration_ms: int
    success: bool
    reason: str | None


class GeminiFallbackOrchestrator:
    """Orchestrates primary and fallback model attempts."""

    def __init__(
        self,
        *,
        settings: Settings,
        discovery_service: ModelDiscoveryService | None,
        timeout_seconds: float,
    ) -> None:
        self._settings = settings
        self._discovery = discovery_service
        self._timeout_seconds = timeout_seconds
        self._max_attempts = settings.GEMINI_MAX_FALLBACK_ATTEMPTS
        self._time_budget = settings.GEMINI_FALLBACK_TIME_BUDGET_SECONDS

    def _create_provider(self, model: str) -> GeminiProvider:
        """Create a provider for the given model."""
        return GeminiProvider(
            api_key=self._settings.GEMINI_API_KEY,
            model=model,
            timeout_seconds=self._timeout_seconds,
        )

    def _is_retryable_error(self, reason: str) -> bool:
        """Determine if an error reason should trigger a fallback attempt."""
        retryable = {
            "rate_limited",
            "unavailable",
            "timeout",
            "model_not_found",
            "malformed_output",
            "validation_error",
            "provider_error",
            "no_usable_hypotheses",
        }
        non_retryable = {
            "config_error",
            "missing_credentials",
            "missing_dependency",
        }
        if reason in retryable:
            return True
        if reason in non_retryable:
            return False
        return True

    def _is_config_error(self, reason: str) -> bool:
        """Check if error is a configuration/auth error that shouldn't be retried."""
        return reason in ("config_error", "missing_credentials")

    async def analyze(
        self,
        request: AnalysisRequest,
        primary_model: str,
    ) -> FallbackResult:
        """Run analysis with primary model and fallbacks.

        Returns the first successful result, or deterministic fallback if
        all attempts fail.
        """
        start_total = time.monotonic()
        attempts: list[AttemptRecord] = []

        # Build the list of models to try: primary first, then discovered fallbacks
        models_to_try: list[str] = [primary_model]
        if self._discovery:
            fallback_models = self._discovery.get_fallback_candidates(
                primary_model, max_candidates=self._max_attempts - 1
            )
            models_to_try.extend(m.model_id for m in fallback_models)

        # Limit total attempts
        models_to_try = models_to_try[:self._max_attempts]

        for attempt_idx, model_id in enumerate(models_to_try, 1):
            # Check time budget
            elapsed = time.monotonic() - start_total
            if elapsed >= self._time_budget:
                logger.warning(
                    "gemini_fallback_time_budget_exceeded",
                    extra={
                        "elapsed_seconds": round(elapsed, 2),
                        "budget_seconds": self._time_budget,
                        "attempts_completed": attempt_idx - 1,
                    },
                )
                break

            provider = self._create_provider(model_id)
            attempt_start = time.monotonic()

            try:
                report = await asyncio.to_thread(provider.analyze, request)
                duration_ms = int((time.monotonic() - attempt_start) * 1000)

                attempts.append(AttemptRecord(
                    model=model_id,
                    attempt_number=attempt_idx,
                    duration_ms=duration_ms,
                    success=True,
                    reason=None,
                ))

                logger.info(
                    "gemini_fallback_success",
                    extra={
                        "model": model_id,
                        "attempt": attempt_idx,
                        "hypotheses": len(report.root_cause_hypotheses),
                        "total_duration_ms": int((time.monotonic() - start_total) * 1000),
                    },
                )

                return FallbackResult(
                    report=report,
                    provider_name="gemini",
                    model=model_id,
                    llm_used=True,
                    attempts=attempts,
                    fallback_used=attempt_idx > 1,
                )

            except LLMProviderError as exc:
                duration_ms = int((time.monotonic() - attempt_start) * 1000)

                attempts.append(AttemptRecord(
                    model=model_id,
                    attempt_number=attempt_idx,
                    duration_ms=duration_ms,
                    success=False,
                    reason=exc.reason,
                ))

                logger.warning(
                    "gemini_fallback_attempt_failed",
                    extra={
                        "model": model_id,
                        "attempt": attempt_idx,
                        "reason": exc.reason,
                        "duration_ms": duration_ms,
                    },
                )

                # Don't retry on config errors
                if self._is_config_error(exc.reason):
                    logger.error(
                        "gemini_config_error_aborting_fallback",
                        extra={"model": model_id, "reason": exc.reason},
                    )
                    break

                # Continue to next model for retryable errors
                if not self._is_retryable_error(exc.reason):
                    logger.warning(
                        "gemini_non_retryable_error_aborting_fallback",
                        extra={"model": model_id, "reason": exc.reason},
                    )
                    break

                # Continue to next model
                continue

            except Exception as exc:  # pragma: no cover - defensive
                duration_ms = int((time.monotonic() - attempt_start) * 1000)

                attempts.append(AttemptRecord(
                    model=model_id,
                    attempt_number=attempt_idx,
                    duration_ms=duration_ms,
                    success=False,
                    reason="unexpected_error",
                ))

                logger.warning(
                    "gemini_fallback_unexpected_error",
                    extra={
                        "model": model_id,
                        "attempt": attempt_idx,
                        "error": str(exc),
                        "duration_ms": duration_ms,
                    },
                )
                continue

        # All attempts failed - use deterministic fallback
        logger.info(
            "gemini_fallback_all_failed_using_deterministic",
            extra={
                "attempts": len(attempts),
                "total_duration_ms": int((time.monotonic() - start_total) * 1000),
                "primary_model": primary_model,
            },
        )

        fallback_engine = DeterministicEngine()
        report = fallback_engine.analyze(request)

        return FallbackResult(
            report=report,
            provider_name=fallback_engine.name,
            model=None,
            llm_used=False,
            attempts=attempts,
            fallback_used=True,
        )


def create_fallback_orchestrator(
    settings: Settings,
    discovery_service: ModelDiscoveryService | None = None,
) -> GeminiFallbackOrchestrator | None:
    """Create a fallback orchestrator if LLM is configured."""
    if not settings.llm_configured:
        return None
    return GeminiFallbackOrchestrator(
        settings=settings,
        discovery_service=discovery_service,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )
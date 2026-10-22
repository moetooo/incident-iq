"""Deterministic fallback analysis engine.

The engine applies fixed rules over the collected evidence. It produces the
same report structure as the LLM provider so the demo keeps working when no
API key is configured or when the provider fails.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.investigation.llm.base import AnalysisRequest, LLMProvider
from app.investigation.llm.schemas import (
    GeneratedHypothesis,
    GeneratedRemediation,
    GeneratedReport,
)


@dataclass
class Rule:
    """One deterministic analysis rule."""

    name: str
    cause: str
    confidence: float
    action: str | None
    explanation: str
    checks: list[str] = field(default_factory=list)
    keywords: tuple[str, ...] = ()


POOL_KEYWORDS = (
    "connection pool",
    "pool exhausted",
    "pool exhaustion",
    "too many connections",
    "max connections",
    "pool timeout",
)

DATABASE_KEYWORDS = (
    "database",
    "postgres",
    "sqlstate",
    "deadlock",
    "db connection",
    "connection refused",
    "connection timed out",
    "connection timeout",
    "could not connect",
)

DEGRADATION_KEYWORDS = (
    "latency",
    "p95",
    "p99",
    "response time",
    "error rate",
    "timeout",
    "timed out",
    "http 500",
    "http 503",
    "5xx",
    "circuit breaker",
)

DEPLOYMENT_KEYWORDS = ("deploy", "rollout", "release", "version ", "config change")


def _blob(summary: str, details: dict) -> str:
    """Return the searchable text of an evidence item."""
    try:
        details_text = json.dumps(details, default=str)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        details_text = str(details)
    return f"{summary} {details_text}".lower()


class DeterministicEngine(LLMProvider):
    """Rule-based RCA engine used as fallback and as a stable test double."""

    name = "deterministic"
    model = None

    def analyze(self, request: AnalysisRequest) -> GeneratedReport:
        """Return a report derived from fixed rules over the evidence."""
        if not request.evidence:
            # No evidence means no supported cause. The report states the gap
            # instead of inventing a hypothesis.
            return GeneratedReport(
                summary=(
                    "No evidence was collected for this incident, so no root cause "
                    "could be established."
                ),
                root_cause_hypotheses=[],
                recommended_checks=[
                    "Collect simulator evidence and re-run the investigation.",
                    "Confirm that the simulator service is reachable.",
                ],
            )

        texts = {
            item.id: _blob(item.summary, item.details) for item in request.evidence
        }

        def matching(keywords: tuple[str, ...]) -> list[str]:
            return [
                item.id
                for item in request.evidence
                if any(keyword in texts[item.id] for keyword in keywords)
            ]

        pool_ids = matching(POOL_KEYWORDS)
        database_ids = matching(DATABASE_KEYWORDS)
        degradation_ids = matching(DEGRADATION_KEYWORDS)
        deployment_ids = [
            item.id
            for item in request.evidence
            if item.type == "deployment"
            or any(keyword in texts[item.id] for keyword in DEPLOYMENT_KEYWORDS)
        ]

        candidates: list[tuple[GeneratedHypothesis, list[GeneratedRemediation], list[str]]] = []

        if deployment_ids and (degradation_ids or database_ids or pool_ids):
            supporting = deployment_ids + degradation_ids + database_ids
            candidates.append(
                (
                    GeneratedHypothesis(
                        cause="Regression introduced by a recent deployment",
                        explanation=(
                            "A deployment event was collected together with error or "
                            "degradation signals, which is consistent with a change-induced "
                            "regression."
                        ),
                        confidence=0.65,
                        evidence_ids=_unique(supporting),
                        recommended_action_type="rollback_demo_deployment",
                    ),
                    [
                        GeneratedRemediation(
                            action="rollback_demo_deployment",
                            parameters={},
                            risk_level="medium",
                            rationale=(
                                "Rolling the demo service back to the previous release is the "
                                "smallest safe step that can confirm or clear a deployment "
                                "regression."
                            ),
                        )
                    ],
                    [
                        "Compare the deployment diff against the error onset time.",
                        "Check whether the error rate returns to baseline after rollback.",
                    ],
                )
            )

        if pool_ids:
            candidates.append(
                (
                    GeneratedHypothesis(
                        cause="Database connection pool exhaustion",
                        explanation=(
                            "Collected evidence reports connection pool pressure, which "
                            "starves request handling and produces timeouts."
                        ),
                        confidence=0.8,
                        evidence_ids=_unique(pool_ids),
                        recommended_action_type="restart_demo_service",
                    ),
                    [
                        GeneratedRemediation(
                            action="restart_demo_service",
                            parameters={},
                            risk_level="medium",
                            rationale=(
                                "Restarting the demo service releases the saturated connection "
                                "pool and restores a clean baseline."
                            ),
                        )
                    ],
                    [
                        "Inspect the pool size and the active connection count.",
                        "Verify that long-running queries release their connections.",
                    ],
                )
            )

        if database_ids:
            candidates.append(
                (
                    GeneratedHypothesis(
                        cause="Database connectivity failure",
                        explanation=(
                            "Collected evidence reports database connection errors that "
                            "correlate with the incident window."
                        ),
                        confidence=0.7,
                        evidence_ids=_unique(database_ids),
                        recommended_action_type="restart_demo_service",
                    ),
                    [
                        GeneratedRemediation(
                            action="restart_demo_service",
                            parameters={},
                            risk_level="medium",
                            rationale=(
                                "Restarting the demo service re-establishes its database "
                                "connections without touching the database itself."
                            ),
                        )
                    ],
                    [
                        "Inspect database connectivity and connection-pool configuration.",
                        "Confirm that the database is reachable from the service network.",
                    ],
                )
            )

        if degradation_ids:
            candidates.append(
                (
                    GeneratedHypothesis(
                        cause="Service latency or error-rate degradation",
                        explanation=(
                            "Collected evidence reports elevated latency or error rates, but "
                            "no single upstream cause is identified."
                        ),
                        confidence=0.5,
                        evidence_ids=_unique(degradation_ids),
                        recommended_action_type="restart_demo_service",
                    ),
                    [
                        GeneratedRemediation(
                            action="restart_demo_service",
                            parameters={},
                            risk_level="medium",
                            rationale=(
                                "A restart is the safest reversible step while the upstream "
                                "cause is still being identified."
                            ),
                        )
                    ],
                    [
                        "Compare latency and error rate against the pre-incident baseline.",
                        "Check downstream dependency health.",
                    ],
                )
            )

        if not candidates:
            candidates.append(
                (
                    GeneratedHypothesis(
                        cause="No matching failure signature in the collected evidence",
                        explanation=(
                            "The collected evidence does not match any known failure "
                            "signature, so the cause remains unknown."
                        ),
                        confidence=0.25,
                        evidence_ids=_unique([item.id for item in request.evidence]),
                        recommended_action_type=None,
                    ),
                    [],
                    [
                        "Collect more evidence and re-run the investigation.",
                        "Check simulator scenario output for the incident window.",
                    ],
                )
            )

        candidates.sort(key=lambda candidate: candidate[0].confidence, reverse=True)

        root_cause, remediations, checks = candidates[0]
        alternative = candidates[1][0] if len(candidates) > 1 else None

        summary = (
            f"Deterministic analysis of {len(request.evidence)} evidence item(s) for "
            f"{request.service}. Most likely cause: {root_cause.cause}."
        )

        return GeneratedReport(
            summary=summary,
            root_cause_hypotheses=[root_cause],
            alternative_hypotheses=[alternative] if alternative else [],
            recommended_checks=checks,
            proposed_remediations=remediations,
        )


def _unique(values: list[str]) -> list[str]:
    """Return the values in order without duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result

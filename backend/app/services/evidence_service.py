"""Evidence collection, normalisation and persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.ids import fingerprint as make_fingerprint
from app.core.logging import get_logger
from app.models.enums import EvidenceType
from app.models.evidence import Evidence
from app.models.incident import Incident
from app.repositories.evidence_repository import EvidenceRepository
from app.services.simulator_client import SimulatorClient

logger = get_logger(__name__)

TYPE_ALIASES: dict[str, EvidenceType] = {
    "log": EvidenceType.LOG,
    "logs": EvidenceType.LOG,
    "error": EvidenceType.LOG,
    "warning": EvidenceType.LOG,
    "application": EvidenceType.LOG,
    "container": EvidenceType.LOG,
    "stdout": EvidenceType.LOG,
    "stderr": EvidenceType.LOG,
    "metric": EvidenceType.METRIC,
    "metrics": EvidenceType.METRIC,
    "timeseries": EvidenceType.METRIC,
    "time_series": EvidenceType.METRIC,
    "gauge": EvidenceType.METRIC,
    "counter": EvidenceType.METRIC,
    "latency": EvidenceType.METRIC,
    "deployment": EvidenceType.DEPLOYMENT,
    "deploy": EvidenceType.DEPLOYMENT,
    "deployments": EvidenceType.DEPLOYMENT,
    "release": EvidenceType.DEPLOYMENT,
    "rollout": EvidenceType.DEPLOYMENT,
    "config_change": EvidenceType.DEPLOYMENT,
    "configuration": EvidenceType.DEPLOYMENT,
    "state": EvidenceType.STATE,
    "health": EvidenceType.STATE,
    "container_state": EvidenceType.STATE,
    "system": EvidenceType.STATE,
    "event": EvidenceType.EVENT,
    "events": EvidenceType.EVENT,
    "alert": EvidenceType.EVENT,
    "alerts": EvidenceType.EVENT,
    "trace": EvidenceType.TRACE,
    "traces": EvidenceType.TRACE,
    "span": EvidenceType.TRACE,
}

HIGH_SIGNAL_TERMS = (
    "error",
    "exception",
    "timeout",
    "timed out",
    "failed",
    "failure",
    "fatal",
    "critical",
    "refused",
    "deadlock",
)

MEDIUM_SIGNAL_TERMS = ("warn", "degraded", "retry", "slow", "elevated", "spike")


@dataclass
class EvidenceCollectionResult:
    """Outcome of one evidence collection run."""

    collected: int
    stored: int
    items: list[Evidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class EvidenceService:
    """Collects evidence from the simulator and stores it for an incident."""

    def __init__(
        self,
        simulator_client: SimulatorClient,
        evidence_repository: EvidenceRepository,
    ) -> None:
        self.simulator_client = simulator_client
        self.evidence_repository = evidence_repository

    def collect(
        self,
        session,
        incident: Incident,
        scenario_id: str | None = None,
    ) -> EvidenceCollectionResult:
        """Fetch, normalise and persist evidence for an incident."""
        warnings: list[str] = []
        raw_items: list[dict[str, Any]] = []

        try:
            raw_items.extend(self.simulator_client.fetch_evidence(scenario_id))
        except Exception as exc:
            warnings.append(f"Could not collect simulator evidence: {exc}")

        try:
            deployments = self.simulator_client.fetch_deployments()
        except Exception as exc:
            warnings.append(f"Could not collect deployment events: {exc}")
            deployments = []

        raw_items.extend(self._as_evidence_items(deployments))

        normalised = self._normalise(raw_items, warnings)

        existing = self.evidence_repository.existing_fingerprints(session, incident.id)
        stored: list[Evidence] = []
        for item in normalised:
            if item["fingerprint"] in existing:
                continue
            existing.add(item["fingerprint"])
            evidence = self.evidence_repository.add(
                session,
                incident_id=incident.id,
                type=item["type"],
                source=item["source"],
                summary=item["summary"],
                details=item["details"],
                confidence=item["confidence"],
                fingerprint=item["fingerprint"],
                timestamp=item["timestamp"],
            )
            stored.append(evidence)

        logger.info(
            "evidence_collected",
            extra={
                "incident_id": incident.id,
                "collected": len(normalised),
                "stored": len(stored),
                "scenario_id": scenario_id,
            },
        )

        return EvidenceCollectionResult(
            collected=len(normalised),
            stored=len(stored),
            items=stored,
            warnings=warnings,
        )

    def list_for_incident(self, session, incident_id: str) -> list[Evidence]:
        """Return the stored evidence of an incident."""
        return self.evidence_repository.list_for_incident(session, incident_id)

    @staticmethod
    def _as_evidence_items(deployments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert deployment events into the evidence item shape.

        The simulator returns deployment events with their own fields
        (``version``, ``deployed_at``, ``changelog``) instead of the generic
        evidence fields. They are mapped here so both sources are stored the
        same way.
        """
        items: list[dict[str, Any]] = []
        for deployment in deployments:
            if deployment.get("type"):
                items.append(deployment)
                continue
            version = deployment.get("version") or "unknown"
            changelog = deployment.get("changelog")
            summary = (
                str(changelog)
                if changelog
                else f"Deployment of version {version} ({deployment.get('status', 'unknown')})"
            )
            items.append(
                {
                    "type": EvidenceType.DEPLOYMENT.value,
                    "source": deployment.get("service") or "payment-api",
                    "timestamp": deployment.get("deployed_at") or deployment.get("timestamp"),
                    "summary": summary,
                    "details": dict(deployment),
                }
            )
        return items

    def _normalise(
        self, raw_items: list[dict[str, Any]], warnings: list[str]
    ) -> list[dict[str, Any]]:
        """Normalise raw simulator payloads into stored evidence items."""
        normalised: list[dict[str, Any]] = []
        for raw in raw_items:
            raw_type = str(raw.get("type") or "").strip().lower()
            evidence_type = TYPE_ALIASES.get(raw_type)
            if evidence_type is None:
                warnings.append(
                    f"Skipped evidence with unsupported type '{raw_type or 'unknown'}'."
                )
                continue

            source = str(raw.get("source") or raw.get("service") or "unknown").strip()
            summary = str(
                raw.get("summary") or raw.get("message") or raw.get("title") or ""
            ).strip()
            details = raw.get("details")
            if not isinstance(details, dict):
                details = {"payload": details} if details is not None else {}

            timestamp = self._parse_timestamp(raw.get("timestamp") or raw.get("time"))
            confidence = self._estimate_confidence(evidence_type, summary, details)

            normalised.append(
                {
                    "type": evidence_type.value,
                    "source": source or "unknown",
                    "summary": summary,
                    "details": details,
                    "confidence": confidence,
                    "timestamp": timestamp,
                    "fingerprint": make_fingerprint(
                        evidence_type.value,
                        source,
                        timestamp.isoformat(),
                        summary,
                    ),
                }
            )
        return normalised

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        """Parse an ISO 8601 timestamp, falling back to now."""
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, str) and value.strip():
            text = value.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(text)
            except ValueError:
                return datetime.now(UTC)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        return datetime.now(UTC)

    @staticmethod
    def _estimate_confidence(
        evidence_type: EvidenceType, summary: str, details: dict[str, Any]
    ) -> float:
        """Estimate the relevance of an evidence item.

        The value is a heuristic relevance score, not a calibrated probability.
        """
        text = f"{summary} {details}".lower()
        if any(term in text for term in HIGH_SIGNAL_TERMS):
            return 0.9
        if evidence_type is EvidenceType.DEPLOYMENT:
            return 0.7
        if any(term in text for term in MEDIUM_SIGNAL_TERMS):
            return 0.6
        if evidence_type is EvidenceType.METRIC:
            return 0.55
        if evidence_type is EvidenceType.STATE:
            return 0.4
        return 0.5

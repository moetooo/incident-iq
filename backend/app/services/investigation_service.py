"""Investigation pipeline.

The pipeline is deliberately a single linear function:

1. move the incident to ``investigating``
2. collect and persist evidence
3. analyse the evidence with the LLM provider, trying fallback models
   on failure, then the deterministic engine when all fail
4. verify every cited evidence id against the collected evidence
5. persist the report, the hypotheses and the remediation proposals
6. move the incident to its next status
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.investigation.deterministic import DeterministicEngine
from app.investigation.llm.base import (
    AnalysisRequest,
    EvidenceItem,
    GeneratedReport,
)
from app.investigation.llm.model_fallback import (
    FallbackResult,
    GeminiFallbackOrchestrator,
)
from app.investigation.validation import verify_report
from app.models.enums import IncidentStatus, RemediationStatus
from app.models.incident import Incident
from app.repositories.incident_repository import IncidentRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.remediation_repository import RemediationRepository
from app.schemas.common import to_iso
from app.schemas.investigation import (
    HypothesisRead,
    InvestigationRead,
    RemediationProposal,
)
from app.services.evidence_service import EvidenceService

logger = get_logger(__name__)


class InvestigationService:
    """Runs investigations for incidents."""

    def __init__(
        self,
        *,
        evidence_service: EvidenceService,
        incident_repository: IncidentRepository,
        investigation_repository: InvestigationRepository,
        remediation_repository: RemediationRepository,
        fallback_orchestrator: GeminiFallbackOrchestrator | None,
        settings: Settings,
        fallback_engine: DeterministicEngine | None = None,
        max_evidence_items: int = 40,
    ) -> None:
        self.evidence_service = evidence_service
        self.incident_repository = incident_repository
        self.investigation_repository = investigation_repository
        self.remediation_repository = remediation_repository
        self.fallback_orchestrator = fallback_orchestrator
        self._settings = settings
        self.fallback_engine = fallback_engine or DeterministicEngine()
        self.max_evidence_items = max_evidence_items

    async def run(
        self,
        session,
        incident: Incident,
        scenario_id: str | None = None,
    ) -> InvestigationRead:
        """Run a full investigation and return the persisted report."""
        warnings: list[str] = []

        self.incident_repository.set_status(session, incident, IncidentStatus.INVESTIGATING)

        collection = self.evidence_service.collect(session, incident, scenario_id)
        warnings.extend(collection.warnings)

        stored_evidence = self.evidence_service.list_for_incident(session, incident.id)
        evidence_items = [
            EvidenceItem(
                id=item.id,
                type=item.type,
                source=item.source,
                timestamp=item.timestamp.isoformat(),
                summary=item.summary,
                details=item.details or {},
                confidence=item.confidence,
            )
            for item in stored_evidence[: self.max_evidence_items]
        ]
        valid_evidence_ids = {item.id for item in evidence_items}

        request = AnalysisRequest(
            incident_id=incident.id,
            title=incident.title,
            service=incident.service,
            severity=incident.severity,
            description=incident.description,
            evidence=evidence_items,
        )

        if self.fallback_orchestrator is None:
            warnings.append(
                "No LLM provider is configured; the deterministic analysis engine was used."
            )
            report, provider_name, model, llm_used = await self._run_fallback_async(
                request, warnings
            )
        else:
            primary_model = self._settings.GEMINI_MODEL
            result: FallbackResult = await self.fallback_orchestrator.analyze(
                request, primary_model
            )
            report = result.report
            provider_name = result.provider_name
            model = result.model
            llm_used = result.llm_used

            for attempt in result.attempts:
                if not attempt.success:
                    next_step = (
                        "trying next model"
                        if attempt.attempt_number < len(result.attempts)
                        else "falling back to deterministic"
                    )
                    warnings.append(
                        f"Gemini model '{attempt.model}' attempt {attempt.attempt_number} "
                        f"failed ({attempt.reason}); {next_step}."
                    )
            if result.fallback_used and not llm_used:
                warnings.append(
                    "All eligible Gemini models failed; the deterministic analysis engine was used."
                )

        report, verification_warnings = verify_report(report, valid_evidence_ids)
        warnings.extend(verification_warnings)

        proposals = self._create_proposals(session, incident, report)

        investigation = self.investigation_repository.create(
            session,
            incident_id=incident.id,
            summary=report.summary,
            llm_used=llm_used,
            provider=provider_name,
            model=model,
            warnings=warnings,
            recommended_checks=list(report.recommended_checks),
            evidence_ids=sorted(valid_evidence_ids),
            knowledge_sources=list(report.knowledge_sources),
            proposed_remediations=[
                proposal.model_dump() for proposal in proposals
            ],
        )

        self.investigation_repository.add_step(
            session,
            investigation_id=investigation.id,
            incident_id=incident.id,
            step_index=1,
            agent_node="evidence",
            action="collect_evidence",
            summary=(
                f"Collected {collection.collected} evidence item(s), stored "
                f"{collection.stored} new item(s)."
            ),
            metadata={
                "collected": collection.collected,
                "stored": collection.stored,
                "scenario_id": scenario_id,
            },
        )
        self.investigation_repository.add_step(
            session,
            investigation_id=investigation.id,
            incident_id=incident.id,
            step_index=2,
            agent_node="analysis",
            action="analyse_evidence",
            summary=(
                f"Analysis produced by {provider_name}"
                f"{f' ({model})' if model else ''}."
            ),
            metadata={"provider": provider_name, "model": model, "llm_used": llm_used},
        )

        hypothesis_reads: list[HypothesisRead] = []
        for kind, hypotheses in (
            ("root_cause", report.root_cause_hypotheses),
            ("alternative", report.alternative_hypotheses),
        ):
            for hypothesis in hypotheses:
                stored = self.investigation_repository.add_hypothesis(
                    session,
                    investigation_id=investigation.id,
                    incident_id=incident.id,
                    kind=_hypothesis_kind(kind),
                    cause=hypothesis.cause,
                    explanation=hypothesis.explanation,
                    confidence=hypothesis.confidence,
                    evidence_ids=hypothesis.evidence_ids,
                    recommended_action_type=hypothesis.recommended_action_type,
                )
                hypothesis_reads.append(
                    HypothesisRead(
                        id=stored.id,
                        kind=stored.kind,
                        cause=stored.cause,
                        explanation=stored.explanation,
                        confidence=stored.confidence,
                        evidence_ids=list(stored.evidence_ids or []),
                        recommended_action_type=stored.recommended_action_type,
                    )
                )

        self.investigation_repository.add_step(
            session,
            investigation_id=investigation.id,
            incident_id=incident.id,
            step_index=3,
            agent_node="remediation",
            action="propose_remediation",
            summary=f"Created {len(proposals)} remediation proposal(s) awaiting approval.",
            metadata={"proposals": [proposal.action for proposal in proposals]},
        )

        if proposals:
            self.incident_repository.set_status(
                session, incident, IncidentStatus.AWAITING_APPROVAL
            )
        else:
            self.incident_repository.set_status(
                session, incident, IncidentStatus.HYPOTHESIS_FORMED
            )

        logger.info(
            "investigation_completed",
            extra={
                "incident_id": incident.id,
                "investigation_id": investigation.id,
                "provider": provider_name,
                "llm_used": llm_used,
                "hypotheses": len(hypothesis_reads),
                "warnings": len(warnings),
            },
        )

        return InvestigationRead(
            id=investigation.id,
            incident_id=incident.id,
            status=investigation.status,
            summary=investigation.summary,
            root_cause_hypotheses=[
                hypothesis for hypothesis in hypothesis_reads if hypothesis.kind == "root_cause"
            ],
            alternative_hypotheses=[
                hypothesis for hypothesis in hypothesis_reads if hypothesis.kind == "alternative"
            ],
            recommended_checks=list(report.recommended_checks),
            proposed_remediations=proposals,
            knowledge_sources=list(report.knowledge_sources),
            evidence_ids=sorted(valid_evidence_ids),
            llm_used=llm_used,
            provider=provider_name,
            model=model,
            warnings=warnings,
            created_at=to_iso(investigation.created_at),
        )

    async def _run_fallback_async(
        self, request: AnalysisRequest, warnings: list[str]
    ) -> tuple[GeneratedReport, str, None, bool]:
        """Run the deterministic engine."""
        report = self.fallback_engine.analyze(request)
        return report, self.fallback_engine.name, None, False

    def _create_proposals(
        self, session, incident: Incident, report: GeneratedReport
    ) -> list[RemediationProposal]:
        """Persist remediation proposals in the ``pending_approval`` state."""
        existing = self.remediation_repository.list_for_incident(session, incident.id)
        pending_actions = {
            remediation.action
            for remediation in existing
            if remediation.status == RemediationStatus.PENDING_APPROVAL.value
        }

        proposals: list[RemediationProposal] = []
        for proposal in report.proposed_remediations:
            if proposal.action in pending_actions:
                continue
            remediation = self.remediation_repository.create(
                session,
                incident_id=incident.id,
                action=proposal.action,
                target_service=incident.service,
                parameters=proposal.parameters,
                risk_level=proposal.risk_level,
                rationale=proposal.rationale,
                requires_human_approval=True,
            )
            self.remediation_repository.add_audit(
                session,
                action_id=remediation.id,
                incident_id=incident.id,
                actor="analysis_engine",
                event_type="created",
                details={
                    "action": proposal.action,
                    "parameters": proposal.parameters,
                    "risk_level": proposal.risk_level,
                },
            )
            pending_actions.add(proposal.action)
            proposals.append(
                RemediationProposal(
                    action=remediation.action,
                    parameters=remediation.parameters or {},
                    risk_level=remediation.risk_level,
                    rationale=remediation.rationale,
                )
            )
        return proposals


def _hypothesis_kind(kind: str):
    from app.models.enums import HypothesisKind

    return HypothesisKind.ROOT_CAUSE if kind == "root_cause" else HypothesisKind.ALTERNATIVE

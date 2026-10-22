"""Verification of analysis output against the evidence actually collected."""

from __future__ import annotations

import re

from app.investigation.llm.schemas import (
    GeneratedHypothesis,
    GeneratedRemediation,
    GeneratedReport,
)
from app.remediation.allowlist import is_allowed

EVIDENCE_ID_PATTERN = re.compile(r"\bev_[A-Za-z0-9_-]{4,}\b")


def verify_report(
    report: GeneratedReport, valid_evidence_ids: set[str]
) -> tuple[GeneratedReport, list[str]]:
    """Verify and sanitise a provider report.

    Every evidence identifier cited by the provider is checked against the
    evidence collected for the incident. Unknown identifiers are removed, and a
    hypothesis that ends up without valid supporting evidence is discarded
    together with a warning. The function never fabricates evidence.
    """
    warnings: list[str] = []
    valid = set(valid_evidence_ids)

    def _verify_hypotheses(
        hypotheses: list[GeneratedHypothesis], kind: str
    ) -> list[GeneratedHypothesis]:
        verified: list[GeneratedHypothesis] = []
        for hypothesis in hypotheses:
            text = f"{hypothesis.cause} {hypothesis.explanation}"
            mentioned = set(EVIDENCE_ID_PATTERN.findall(text))
            unknown_mentions = sorted(mentioned - valid)
            if unknown_mentions:
                warnings.append(
                    f"Discarded {kind} hypothesis '{hypothesis.cause[:80]}': it referenced "
                    f"unknown evidence id(s) {', '.join(unknown_mentions)}."
                )
                continue

            unknown_citations = [
                evidence_id for evidence_id in hypothesis.evidence_ids if evidence_id not in valid
            ]
            kept = [
                evidence_id for evidence_id in hypothesis.evidence_ids if evidence_id in valid
            ]
            if unknown_citations:
                warnings.append(
                    f"Removed unknown evidence id(s) {', '.join(unknown_citations)} from "
                    f"{kind} hypothesis '{hypothesis.cause[:80]}'."
                )
            if not kept:
                warnings.append(
                    f"Discarded {kind} hypothesis '{hypothesis.cause[:80]}': no supporting "
                    "evidence was collected for this incident."
                )
                continue

            action = hypothesis.recommended_action_type
            if action and not is_allowed(action):
                warnings.append(
                    f"Ignored unsupported remediation action '{action}' proposed by the "
                    "analysis engine."
                )
                action = None

            verified.append(
                GeneratedHypothesis(
                    cause=hypothesis.cause,
                    explanation=hypothesis.explanation,
                    confidence=hypothesis.confidence,
                    evidence_ids=kept,
                    recommended_action_type=action,
                )
            )
        return verified

    remediations: list[GeneratedRemediation] = []
    for remediation in report.proposed_remediations:
        if not is_allowed(remediation.action):
            warnings.append(
                f"Rejected unsupported remediation action '{remediation.action}' proposed by "
                "the analysis engine."
            )
            continue
        remediations.append(remediation)

    return (
        GeneratedReport(
            summary=report.summary,
            root_cause_hypotheses=_verify_hypotheses(
                report.root_cause_hypotheses, "root-cause"
            ),
            alternative_hypotheses=_verify_hypotheses(
                report.alternative_hypotheses, "alternative"
            ),
            recommended_checks=list(report.recommended_checks),
            proposed_remediations=remediations,
            knowledge_sources=list(report.knowledge_sources),
        ),
        warnings,
    )

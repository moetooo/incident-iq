"""Prompt construction for the Gemini analysis provider."""

from __future__ import annotations

import json

from app.investigation.llm.base import AnalysisRequest
from app.remediation.allowlist import ALLOWED_ACTIONS

SYSTEM_INSTRUCTION = """\
You are the IncidentIQ incident analysis engine. You analyse operational \
evidence and produce a root-cause analysis for a software engineering / SRE \
audience.

Rules you must follow:
1. Use ONLY the evidence identifiers listed in the "Evidence" section. Never \
invent, guess or renumber an evidence identifier.
2. Every hypothesis must cite at least one evidence identifier from that list. \
A hypothesis without supporting evidence is invalid and will be discarded.
3. `confidence` is your own estimate between 0 and 1. It is not a calibrated \
probability. Do not claim that a cause is proven.
4. Describe the cause as a hypothesis. Never state a hypothesis as a verified \
fact and never claim that you executed or verified a fix.
5. `recommended_action_type` and `proposed_remediations[].action` may only be \
one of the allowed actions listed below. Use an empty string when no action \
is justified.
6. `proposed_remediations` are proposals only. They require human approval \
before anything is executed.
7. If the evidence is insufficient, return an empty list of hypotheses and \
say so in the summary.
8. Never fabricate metrics, logs, deployments or identifiers that are not in \
the evidence list.
"""


def build_prompt(request: AnalysisRequest) -> str:
    """Build the full prompt sent to the provider."""
    allowed = ", ".join(sorted(ALLOWED_ACTIONS))
    sections = [
        SYSTEM_INSTRUCTION,
        f"Allowed remediation actions: {allowed}",
        "",
        "Incident:",
        f"  id: {request.incident_id}",
        f"  title: {request.title}",
        f"  service: {request.service}",
        f"  severity: {request.severity}",
        f"  description: {request.description or '(none provided)'}",
        "",
    ]

    if request.evidence:
        sections.append("Evidence:")
        for item in request.evidence:
            sections.append(item.to_prompt_line())
            if item.details:
                details = json.dumps(item.details, default=str)
                if len(details) > 800:
                    details = details[:800] + "...(truncated)"
                sections.append(f"  details: {details}")
    else:
        sections.append("Evidence: none collected.")

    sections.append("")
    sections.append(
        "Return the JSON object with keys: summary, root_cause_hypotheses, "
        "alternative_hypotheses, recommended_checks, proposed_remediations."
    )
    return "\n".join(sections)

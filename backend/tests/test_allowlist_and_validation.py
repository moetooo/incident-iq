"""Allowlist and evidence verification tests."""

from __future__ import annotations

import pytest

from app.core.errors import InvalidParametersError, UnsupportedActionError
from app.investigation.llm.schemas import (
    GeneratedHypothesis,
    GeneratedRemediation,
    GeneratedReport,
)
from app.investigation.validation import verify_report
from app.remediation.allowlist import ALLOWED_ACTIONS, get_spec, is_allowed


def test_only_documented_actions_are_allowlisted():
    assert ALLOWED_ACTIONS == {
        "rollback_demo_deployment",
        "restart_demo_service",
        "scale_demo_instances",
        "clear_demo_cache",
    }


def test_unknown_action_is_rejected():
    with pytest.raises(UnsupportedActionError):
        get_spec("drop_database")


def test_unknown_parameters_are_rejected():
    with pytest.raises(InvalidParametersError):
        get_spec("restart_demo_service").validate_parameters({"command": "rm -rf /"})


def test_required_parameters_are_enforced():
    with pytest.raises(InvalidParametersError):
        get_spec("scale_demo_instances").validate_parameters({})


def test_integer_parameters_are_range_checked():
    spec = get_spec("scale_demo_instances")

    assert spec.validate_parameters({"instances": 3}) == {"instances": 3}
    with pytest.raises(InvalidParametersError):
        spec.validate_parameters({"instances": 0})
    with pytest.raises(InvalidParametersError):
        spec.validate_parameters({"instances": 11})
    with pytest.raises(InvalidParametersError):
        spec.validate_parameters({"instances": "3"})


def test_verification_drops_unknown_evidence_ids():
    report = GeneratedReport(
        summary="summary",
        root_cause_hypotheses=[
            GeneratedHypothesis(
                cause="Pool exhaustion",
                confidence=0.8,
                evidence_ids=["ev_valid", "ev_fake"],
            )
        ],
    )

    verified, warnings = verify_report(report, {"ev_valid"})

    assert verified.root_cause_hypotheses[0].evidence_ids == ["ev_valid"]
    assert warnings


def test_verification_drops_hypotheses_without_evidence():
    report = GeneratedReport(
        summary="summary",
        root_cause_hypotheses=[
            GeneratedHypothesis(cause="Unsupported", confidence=0.9, evidence_ids=["ev_fake"])
        ],
    )

    verified, warnings = verify_report(report, {"ev_valid"})

    assert verified.root_cause_hypotheses == []
    assert warnings


def test_verification_drops_hypotheses_that_mention_unknown_ids_in_text():
    report = GeneratedReport(
        summary="summary",
        root_cause_hypotheses=[
            GeneratedHypothesis(
                cause="Pool exhaustion",
                explanation="Seen in ev_deadbeefdead",
                confidence=0.8,
                evidence_ids=["ev_valid"],
            )
        ],
    )

    verified, warnings = verify_report(report, {"ev_valid"})

    assert verified.root_cause_hypotheses == []
    assert warnings


def test_verification_removes_unsupported_actions():
    report = GeneratedReport(
        summary="summary",
        root_cause_hypotheses=[
            GeneratedHypothesis(
                cause="Pool exhaustion",
                confidence=0.8,
                evidence_ids=["ev_valid"],
                recommended_action_type="delete_everything",
            )
        ],
        proposed_remediations=[
            GeneratedRemediation(action="delete_everything", parameters={}),
        ],
    )

    verified, warnings = verify_report(report, {"ev_valid"})

    assert verified.root_cause_hypotheses[0].recommended_action_type is None
    assert verified.proposed_remediations == []
    assert warnings


def test_is_allowed_helper():
    assert is_allowed("restart_demo_service")
    assert not is_allowed("restart_everything")

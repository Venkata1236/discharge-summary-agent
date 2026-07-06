import pytest
from agents.state import AgentState, DischargeSummary, MISSING
from agents.nodes.safety_guardrail import safety_guardrail_node


def test_missing_fields_get_flagged():
    """Empty fields must be replaced with MISSING, never left blank"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            patient_name="",
            allergies="",
            discharge_condition=""
        )
    )
    result = safety_guardrail_node(state)
    assert result.summary.patient_name == MISSING
    assert result.summary.allergies == MISSING
    assert result.summary.discharge_condition == MISSING


def test_draft_disclaimer_always_added():
    """DRAFT ONLY flag must always be present in output"""
    state = AgentState(patient_folder="test")
    result = safety_guardrail_node(state)
    draft_flags = [f for f in result.summary.flags if "DRAFT ONLY" in f]
    assert len(draft_flags) == 1


def test_unresolved_conflicts_get_flagged():
    """Conflicts in summary must be escalated to flags"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            conflicts=["CONFLICT in creatinine: 1.65 vs 0.85"]
        )
    )
    result = safety_guardrail_node(state)
    conflict_flags = [f for f in result.summary.flags if "UNRESOLVED CONFLICTS" in f]
    assert len(conflict_flags) == 1


def test_allergies_critical_flag():
    """Unknown allergy status must trigger CRITICAL flag"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(allergies=MISSING)
    )
    result = safety_guardrail_node(state)
    critical_flags = [f for f in result.summary.flags if "CRITICAL" in f]
    assert len(critical_flags) == 1


def test_guardrail_never_removes_existing_flags():
    """Safety guardrail must only ADD flags, never remove existing ones"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            flags=["EXISTING FLAG - some issue"]
        )
    )
    result = safety_guardrail_node(state)
    assert "EXISTING FLAG - some issue" in result.summary.flags
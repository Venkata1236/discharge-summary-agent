import pytest
from agents.state import AgentState, DischargeSummary, Medication, MISSING
from agents.nodes.med_reconciliation import med_reconciliation_node


def test_stopped_medication_flagged():
    """Medication present at admission but absent at discharge must be flagged"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            admission_medications=[
                Medication(name="Metformin", dose="500mg", frequency="BD", route="oral")
            ],
            discharge_medications=[]
        )
    )
    result = med_reconciliation_node(state)
    stopped = [c for c in result.summary.medication_changes if c.change_type == "stopped"]
    assert len(stopped) == 1
    assert stopped[0].medication == "Metformin"


def test_added_medication_detected():
    """New medication at discharge not present at admission must be detected"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            admission_medications=[],
            discharge_medications=[
                Medication(name="Pantoprazole", dose="40mg", frequency="OD", route="oral")
            ]
        )
    )
    result = med_reconciliation_node(state)
    added = [c for c in result.summary.medication_changes if c.change_type == "added"]
    assert len(added) == 1
    assert added[0].medication == "Pantoprazole"


def test_empty_both_lists_flagged():
    """Both lists missing must raise a flag, not crash"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            admission_medications=[],
            discharge_medications=[]
        )
    )
    result = med_reconciliation_node(state)
    assert any("RECONCILIATION SKIPPED" in f for f in result.summary.flags)


def test_dose_change_flagged():
    """Same medication with different dose must be flagged"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            admission_medications=[
                Medication(name="Amlodipine", dose="5mg", frequency="OD", route="oral")
            ],
            discharge_medications=[
                Medication(name="Amlodipine", dose="10mg", frequency="OD", route="oral")
            ]
        )
    )
    result = med_reconciliation_node(state)
    changed = [c for c in result.summary.medication_changes if c.change_type == "dose_changed"]
    assert len(changed) == 1


def test_case_insensitive_matching():
    """Medication names with different casing must be treated as the same drug"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            admission_medications=[
                Medication(name="METFORMIN", dose="500mg", frequency="BD", route="oral")
            ],
            discharge_medications=[
                Medication(name="metformin", dose="500mg", frequency="BD", route="oral")
            ]
        )
    )
    result = med_reconciliation_node(state)
    assert len(result.summary.medication_changes) == 0


def test_missing_medication_name_excluded():
    """A medication with MISSING as its name must not create false comparisons"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            admission_medications=[
                Medication(name=MISSING, dose="500mg", frequency="BD", route="oral")
            ],
            discharge_medications=[]
        )
    )
    result = med_reconciliation_node(state)
    stopped = [c for c in result.summary.medication_changes if c.medication == MISSING]
    assert len(stopped) == 0
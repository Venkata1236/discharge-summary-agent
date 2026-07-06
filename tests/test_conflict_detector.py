import pytest
from unittest.mock import patch, MagicMock
from agents.state import AgentState, DischargeSummary


def test_no_raw_text_does_not_crash():
    """Conflict detector must handle empty raw text gracefully"""
    from agents.nodes.conflict_detector import conflict_detector_node
    state = AgentState(
        patient_folder="test",
        raw_text={},
        summary=DischargeSummary()
    )
    result = conflict_detector_node(state)
    assert result is not None


def test_conflicts_stored_in_state():
    """Detected conflicts must be stored in summary.conflicts"""
    state = AgentState(
        patient_folder="test",
        summary=DischargeSummary(
            conflicts=["CONFLICT in creatinine"]
        )
    )
    assert len(state.summary.conflicts) == 1


@patch("agents.nodes.conflict_detector.client")
def test_llm_failure_handled_gracefully(mock_client):
    """If the LLM call fails, the node must not crash and must log an error"""
    from agents.nodes.conflict_detector import conflict_detector_node
    mock_client.messages.create.side_effect = Exception("API timeout")

    state = AgentState(
        patient_folder="test",
        raw_text={"doc1.pdf": "some clinical text"},
        summary=DischargeSummary()
    )
    result = conflict_detector_node(state)
    assert len(result.errors) > 0
    assert "conflict_detector failed" in result.errors[0]


@patch("agents.nodes.conflict_detector.client")
def test_malformed_json_response_handled(mock_client):
    """If the LLM returns invalid JSON, the node must not crash"""
    from agents.nodes.conflict_detector import conflict_detector_node
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json {{{")]
    mock_client.messages.create.return_value = mock_response

    state = AgentState(
        patient_folder="test",
        raw_text={"doc1.pdf": "some clinical text"},
        summary=DischargeSummary()
    )
    result = conflict_detector_node(state)
    assert len(result.errors) > 0
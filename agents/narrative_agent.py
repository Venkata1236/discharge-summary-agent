from agents.state import AgentState
from agents.nodes.extractor import extractor_node


# ─────────────────────────────────────────────
# NARRATIVE AGENT
# ─────────────────────────────────────────────
#
# Owns the clinical narrative domain: demographics, diagnoses,
# hospital course, and procedures. Wraps the existing extractor_node —
# no extraction logic is rewritten here, just sequenced.
# ─────────────────────────────────────────────

NARRATIVE_TASKS = [
    "extract_demographics",
    "extract_diagnoses",
    "extract_hospital_course",
    "extract_procedures",
]


class NarrativeAgent:
    def run(self, state: AgentState) -> AgentState:
        print("[NARRATIVE AGENT] Extracting demographics, diagnoses, hospital course, procedures...")

        for task in NARRATIVE_TASKS:
            state.current_task = task
            state = extractor_node(state)

        print("[NARRATIVE AGENT] ✓ Done")
        return state
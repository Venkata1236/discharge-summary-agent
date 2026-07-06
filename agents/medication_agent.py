from agents.state import AgentState
from agents.nodes.extractor import extractor_node
from agents.nodes.med_reconciliation import med_reconciliation_node


# ─────────────────────────────────────────────
# MEDICATION AGENT
# ─────────────────────────────────────────────
#
# Owns the medication domain: extracts admission and discharge
# medications, then immediately runs deterministic reconciliation
# against them. Wraps extractor_node and med_reconciliation_node —
# neither is rewritten, just called in sequence here instead of
# waiting for the planner to schedule them separately.
# ─────────────────────────────────────────────

MEDICATION_EXTRACTION_TASKS = [
    "extract_admission_medications",
    "extract_discharge_medications",
]


class MedicationAgent:
    def run(self, state: AgentState) -> AgentState:
        print("[MEDICATION AGENT] Extracting admission and discharge medications...")

        for task in MEDICATION_EXTRACTION_TASKS:
            state.current_task = task
            state = extractor_node(state)

        print("[MEDICATION AGENT] Running deterministic reconciliation...")
        state = med_reconciliation_node(state)

        print("[MEDICATION AGENT] ✓ Done")
        return state
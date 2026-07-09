from agents.state import AgentState, MISSING
from agents.nodes.extractor import extractor_node
from agents.icd_mapper import map_to_icd10


# ─────────────────────────────────────────────
# NARRATIVE AGENT
# ─────────────────────────────────────────────
#
# Owns the clinical narrative domain: demographics, diagnoses,
# hospital course, and procedures. Wraps the existing extractor_node —
# no extraction logic is rewritten here, just sequenced. Also maps the
# extracted principal diagnosis to an ICD-10 code once extraction
# completes.
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

        diagnosis_value = state.summary.principal_diagnosis.value
        if diagnosis_value and diagnosis_value != MISSING:
            print("[NARRATIVE AGENT] Mapping principal diagnosis to ICD-10...")
            state.summary.principal_diagnosis_icd10 = map_to_icd10(diagnosis_value)
        else:
            print("[NARRATIVE AGENT] Skipping ICD-10 mapping — no diagnosis extracted")

        print("[NARRATIVE AGENT] ✓ Done")
        return state
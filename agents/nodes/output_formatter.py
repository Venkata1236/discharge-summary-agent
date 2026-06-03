import json
from datetime import datetime
from agents.state import AgentState, MISSING


# ─────────────────────────────────────────────
# OUTPUT FORMATTER NODE
# ─────────────────────────────────────────────

def output_formatter_node(state: AgentState) -> AgentState:
    """
    Final node — formats the discharge summary and trace into
    clean structured output for terminal display.
    No LLM calls — pure formatting only.
    """

    state.trace.append({
        "step": state.step_count,
        "node": "output_formatter",
        "action": "formatting final discharge summary and trace",
    })

    print(f"\n[OUTPUT FORMATTER] Building final output...")

    summary = state.summary

    # ── Build structured discharge summary dict ──
    discharge_summary = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "agent_steps": state.step_count,
            "total_flags": len(summary.flags),
            "total_conflicts": len(summary.conflicts),
            "status": "DRAFT - Clinician Review Required"
        },
        "patient_demographics": {
            "name": summary.patient_name,
            "id": summary.patient_id,
            "age_sex": summary.age_sex,
            "dob": summary.dob,
        },
        "admission_details": {
            "admission_date": summary.admission_date,
            "discharge_date": summary.discharge_date,
            "consultant": summary.consultant,
            "ward": summary.ward,
        },
        "diagnoses": {
            "principal": summary.principal_diagnosis,
            "secondary": summary.secondary_diagnoses or [],
        },
        "clinical": {
            "hospital_course": summary.hospital_course,
            "procedures": summary.procedures or [],
        },
        "medications": {
            "admission": [m.model_dump() for m in summary.admission_medications],
            "discharge": [m.model_dump() for m in summary.discharge_medications],
            "changes": [c.model_dump() for c in summary.medication_changes],
        },
        "safety": {
            "allergies": summary.allergies,
            "discharge_condition": summary.discharge_condition,
        },
        "follow_up": {
            "instructions": summary.follow_up_instructions or [],
            "pending_results": summary.pending_results or [],
        },
        "flags_and_conflicts": {
            "flags": summary.flags,
            "conflicts": summary.conflicts,
        }
    }

    # ── Print discharge summary to terminal ──
    _print_separator("DISCHARGE SUMMARY")
    print(json.dumps(discharge_summary, indent=2))

    # ── Print agent trace to terminal ──
    _print_separator("AGENT TRACE")
    for step in state.trace:
        print(json.dumps(step, indent=2))

    # ── Print flags summary ──
    _print_separator("FLAGS REQUIRING CLINICIAN REVIEW")
    if summary.flags:
        for i, flag in enumerate(summary.flags, 1):
            print(f"  {i}. {flag}")
    else:
        print("  No flags raised.")

    # ── Print errors if any ──
    if state.errors:
        _print_separator("ERRORS ENCOUNTERED")
        for err in state.errors:
            print(f"  ✗ {err}")

    _print_separator("END OF REPORT")

    state.is_complete = True
    state.step_count += 1
    return state


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _print_separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")
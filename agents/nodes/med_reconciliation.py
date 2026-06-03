import json
import anthropic
from agents.state import AgentState, MedicationChange, MISSING


# ─────────────────────────────────────────────
# CLIENT — created once at module level
# ─────────────────────────────────────────────

client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# MED RECONCILIATION NODE
# ─────────────────────────────────────────────

def med_reconciliation_node(state: AgentState) -> AgentState:
    """
    Compares admission medications vs discharge medications.
    Flags:
    - New medications added at discharge
    - Medications stopped without explanation
    - Dose changes without explanation
    - Any unexplained change
    Never assumes a change is intentional — always flags for clinician.
    """

    state.trace.append({
        "step": state.step_count,
        "node": "med_reconciliation",
        "action": "comparing admission vs discharge medications",
    })

    print(f"[MED RECONCILIATION] Comparing admission vs discharge meds...")

    # Get medication lists from state
    admission_meds = [m.model_dump() for m in state.summary.admission_medications]
    discharge_meds = [m.model_dump() for m in state.summary.discharge_medications]

    # If either list is empty — flag and skip
    if not admission_meds and not discharge_meds:
        msg = "RECONCILIATION SKIPPED - Both admission and discharge medication lists are missing"
        state.summary.flags.append(msg)
        print(f"[MED RECONCILIATION] ⚠ {msg}")
        state = _advance_plan(state)
        state.step_count += 1
        return state

    if not admission_meds:
        msg = "RECONCILIATION INCOMPLETE - Admission medications missing — cannot compare"
        state.summary.flags.append(msg)
        print(f"[MED RECONCILIATION] ⚠ {msg}")
        state = _advance_plan(state)
        state.step_count += 1
        return state

    if not discharge_meds:
        msg = "RECONCILIATION INCOMPLETE - Discharge medications missing — cannot compare"
        state.summary.flags.append(msg)
        print(f"[MED RECONCILIATION] ⚠ {msg}")
        state = _advance_plan(state)
        state.step_count += 1
        return state

    prompt = f"""
You are a clinical pharmacist performing medication reconciliation.

ADMISSION MEDICATIONS:
{json.dumps(admission_meds, indent=2)}

DISCHARGE MEDICATIONS:
{json.dumps(discharge_meds, indent=2)}

Compare the two lists carefully and identify ALL changes.

For each change classify it as one of:
- "added"         → new medication at discharge not present at admission
- "stopped"       → admission medication not continued at discharge
- "dose_changed"  → same medication but different dose or frequency
- "unexplained"   → change exists but reason cannot be determined from the data

Rules:
- Flag ALL changes — do not assume any change is intentional
- If a medication appears in both lists with same dose/frequency → it is unchanged, do not include
- If reason for change is not explicitly stated in the data → mark as "unexplained"
- Never invent reasons for changes

Return ONLY valid JSON:
{{
    "medication_changes": [
        {{
            "medication": "medication name",
            "change_type": "added | stopped | dose_changed | unexplained",
            "note": "brief description of the change"
        }}
    ],
    "reconciliation_summary": "one line summary of overall changes"
}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        changes = result.get("medication_changes", [])
        summary_line = result.get("reconciliation_summary", "")

        # Store changes in state
        state.summary.medication_changes = [
            MedicationChange(**c) for c in changes
        ]

        # Flag unexplained changes
        unexplained = [c for c in changes if c.get("change_type") == "unexplained"]
        for u in unexplained:
            flag = f"UNEXPLAINED MED CHANGE - {u.get('medication')}: {u.get('note')} — Clinician Review Required"
            state.summary.flags.append(flag)
            print(f"[MED RECONCILIATION] ⚠ {flag}")

        print(f"[MED RECONCILIATION] ✓ {len(changes)} change(s) found — {len(unexplained)} unexplained")
        print(f"[MED RECONCILIATION] Summary: {summary_line}")

        state.trace.append({
            "step": state.step_count,
            "node": "med_reconciliation",
            "result": f"{len(changes)} medication change(s) identified",
            "changes": changes,
            "summary": summary_line
        })

    except Exception as e:
        print(f"[MED RECONCILIATION] ✗ Failed: {e}")
        state.errors.append(f"med_reconciliation failed: {e}")

    # Advance plan
    state = _advance_plan(state)
    state.step_count += 1
    return state


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _advance_plan(state: AgentState) -> AgentState:
    if state.plan:
        state.plan.pop(0)
    state.current_task = state.plan[0] if state.plan else "format_output"
    return state
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
    Compares admission vs discharge medications using deterministic
    Python set logic — no LLM involved in the comparison itself.
    LLM is only used for the final narrative summary line.
    Flags: added, stopped, dose_changed, unexplained.
    """

    state.trace.append({
        "step": state.step_count,
        "node": "med_reconciliation",
        "action": "comparing admission vs discharge medications (deterministic)",
    })

    print(f"[MED RECONCILIATION] Comparing admission vs discharge meds...")

    admission_meds = state.summary.admission_medications
    discharge_meds = state.summary.discharge_medications

    # ── Guard: missing lists ──
    if not admission_meds and not discharge_meds:
        _flag(state, "RECONCILIATION SKIPPED - Both medication lists missing")
        return _done(state)

    if not admission_meds:
        _flag(state, "RECONCILIATION INCOMPLETE - Admission medications missing")
        return _done(state)

    if not discharge_meds:
        _flag(state, "RECONCILIATION INCOMPLETE - Discharge medications missing")
        return _done(state)

    # ── Build lookup dicts keyed by lowercase med name ──
    admission_map = {
        m.name.strip().lower(): m for m in admission_meds
        if m.name != MISSING
    }
    discharge_map = {
        m.name.strip().lower(): m for m in discharge_meds
        if m.name != MISSING
    }

    admission_names = set(admission_map.keys())
    discharge_names = set(discharge_map.keys())

    changes = []

    # ── Added: in discharge but not admission ──
    for name in discharge_names - admission_names:
        med = discharge_map[name]
        changes.append(MedicationChange(
            medication=med.name,
            change_type="added",
            note=f"New at discharge — {med.dose} {med.frequency} {med.route}".strip()
        ))
        print(f"[MED RECONCILIATION] + ADDED: {med.name}")

    # ── Stopped: in admission but not discharge ──
    for name in admission_names - discharge_names:
        med = admission_map[name]
        changes.append(MedicationChange(
            medication=med.name,
            change_type="stopped",
            note=f"Present at admission but not at discharge — {med.dose} {med.frequency}".strip()
        ))
        flag = f"UNEXPLAINED STOP - {med.name} not continued at discharge — Clinician Review Required"
        state.summary.flags.append(flag)
        print(f"[MED RECONCILIATION] ⚠ STOPPED: {med.name}")

    # ── Dose/frequency changed: in both but different values ──
    for name in admission_names & discharge_names:
        a = admission_map[name]
        d = discharge_map[name]

        dose_changed = (
            a.dose != MISSING and d.dose != MISSING and a.dose != d.dose
        )
        freq_changed = (
            a.frequency != MISSING and d.frequency != MISSING
            and a.frequency != d.frequency
        )

        if dose_changed or freq_changed:
            note = f"Admission: {a.dose} {a.frequency} → Discharge: {d.dose} {d.frequency}"
            changes.append(MedicationChange(
                medication=a.name,
                change_type="dose_changed",
                note=note.strip()
            ))
            flag = f"UNEXPLAINED DOSE CHANGE - {a.name}: {note} — Clinician Review Required"
            state.summary.flags.append(flag)
            print(f"[MED RECONCILIATION] ⚠ DOSE CHANGED: {a.name}")

    # Store all changes
    state.summary.medication_changes = changes

    unexplained_count = sum(
        1 for c in changes if c.change_type in ("stopped", "dose_changed")
    )

    print(f"[MED RECONCILIATION] ✓ {len(changes)} change(s) — {unexplained_count} flagged")

    state.trace.append({
        "step": state.step_count,
        "node": "med_reconciliation",
        "result": f"{len(changes)} change(s), {unexplained_count} flagged",
        "changes": [c.model_dump() for c in changes]
    })

    return _done(state)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _flag(state: AgentState, msg: str) -> None:
    state.summary.flags.append(msg)
    print(f"[MED RECONCILIATION] ⚠ {msg}")


def _done(state: AgentState) -> AgentState:
    if state.plan:
        state.plan.pop(0)
    state.current_task = state.plan[0] if state.plan else "format_output"
    state.step_count += 1
    return state
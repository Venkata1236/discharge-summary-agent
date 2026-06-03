import json
import anthropic
from agents.state import AgentState, MISSING


# ─────────────────────────────────────────────
# CLIENT — created once at module level
# ─────────────────────────────────────────────

client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# CONFLICT DETECTOR NODE
# ─────────────────────────────────────────────

def conflict_detector_node(state: AgentState) -> AgentState:
    """
    Cross-checks clinical notes against each other.
    If two notes disagree on the same fact — flag it.
    Never picks one version over the other — always escalates to clinician.
    """

    state.trace.append({
        "step": state.step_count,
        "node": "conflict_detector",
        "action": "scanning for contradictions across notes",
    })

    print(f"[CONFLICT DETECTOR] Scanning for contradictions...")

    full_text = _combine_raw_text(state.raw_text)
    summary_snapshot = json.dumps(state.summary.model_dump(), indent=2)

    prompt = f"""
You are a clinical conflict detector reviewing hospital notes for contradictions.

CLINICAL TEXT FROM ALL DOCUMENTS:
{full_text}

CURRENT EXTRACTED SUMMARY:
{summary_snapshot}

Your job is to find contradictions between different documents or notes.
Examples of conflicts to look for:
- Age or gender mentioned differently in two notes
- Diagnosis mentioned in one note but contradicted in another
- Medication dose listed differently in admission note vs drug chart
- Allergy mentioned in one note but ignored in medication chart
- Discharge date inconsistent across documents
- Lab values reported differently in different notes
- Conflicting statements about patient condition

Rules:
- Only flag REAL contradictions — not missing data
- Do NOT pick which version is correct — flag both versions
- If no conflicts found, return empty list
- Be specific — quote the conflicting values and their source documents

Return ONLY valid JSON:
{{
    "conflicts": [
        {{
            "field": "field name where conflict exists",
            "version_1": "what document A says",
            "version_2": "what document B says",
            "source_1": "document/page where version 1 was found",
            "source_2": "document/page where version 2 was found",
            "flag": "CONFLICT - Clinician Review Required"
        }}
    ]
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

        conflicts = result.get("conflicts", [])

        if conflicts:
            print(f"[CONFLICT DETECTOR] ⚠ {len(conflicts)} conflict(s) found")
            for c in conflicts:
                conflict_str = (
                    f"CONFLICT in '{c.get('field')}': "
                    f"'{c.get('version_1')}' ({c.get('source_1')}) "
                    f"vs '{c.get('version_2')}' ({c.get('source_2')})"
                )
                state.summary.conflicts.append(conflict_str)
                state.summary.flags.append(conflict_str)
                print(f"[CONFLICT DETECTOR] {conflict_str}")
        else:
            print(f"[CONFLICT DETECTOR] ✓ No conflicts found")

        state.trace.append({
            "step": state.step_count,
            "node": "conflict_detector",
            "result": f"{len(conflicts)} conflict(s) detected",
            "conflicts": conflicts
        })

    except Exception as e:
        print(f"[CONFLICT DETECTOR] ✗ Failed: {e}")
        state.errors.append(f"conflict_detector failed: {e}")

    # Advance plan
    state = _advance_plan(state)
    state.step_count += 1
    return state


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _combine_raw_text(raw_text: dict[str, str]) -> str:
    parts = []
    for filename, text in raw_text.items():
        parts.append(f"=== {filename} ===\n{text}")
    return "\n\n".join(parts)


def _advance_plan(state: AgentState) -> AgentState:
    if state.plan:
        state.plan.pop(0)
    state.current_task = state.plan[0] if state.plan else "format_output"
    return state
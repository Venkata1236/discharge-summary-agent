import json
import anthropic
from agents.state import AgentState


# ─────────────────────────────────────────────
# CLIENT — created once at module level
# ─────────────────────────────────────────────

client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# PLANNER NODE
# ─────────────────────────────────────────────

def planner_node(state: AgentState) -> AgentState:
    """
    LLM looks at what's been extracted so far and decides
    what to do next. Re-plans after every step.
    This is what makes it a real agent loop — not a fixed pipeline.
    """

    # Log trace
    state.trace.append({
        "step": state.step_count,
        "node": "planner",
        "action": "generating plan",
        "input": f"current_task: {state.current_task or 'none'}",
    })

    # Build context of what's already been extracted
    summary_snapshot = state.summary.model_dump()
    already_done = [
        field for field, value in summary_snapshot.items()
        if value != "[MISSING - Clinician Review Required]"
        and value != "[PENDING - Awaiting Result]"
        and value not in [[], {}]
    ]

    prompt = f"""
You are a clinical AI agent planning the next step to build a discharge summary.

RAW CLINICAL TEXT AVAILABLE:
{_format_raw_text(state.raw_text)}

FIELDS ALREADY EXTRACTED:
{already_done}

CURRENT SUMMARY STATE:
{json.dumps(summary_snapshot, indent=2)}

PREVIOUS PLAN:
{state.plan}

Based on what is still missing, decide the next ordered list of tasks to complete the discharge summary.

Available tasks:
- extract_demographics
- extract_diagnoses
- extract_hospital_course
- extract_procedures
- extract_admission_medications
- extract_discharge_medications
- reconcile_medications
- detect_conflicts
- check_pending_results
- call_drug_interaction_tool
- call_flag_review_tool
- call_pending_checker_tool
- apply_safety_guardrail
- format_output

Rules:
- Only include tasks that are still needed
- If all fields are filled, return ["format_output"]
- Always end with apply_safety_guardrail then format_output
- Return ONLY a valid JSON array of task strings, nothing else

Example: ["extract_diagnoses", "reconcile_medications", "apply_safety_guardrail", "format_output"]
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback plan if LLM returns something unexpected
        print(f"[PLANNER] Failed to parse plan — using fallback")
        plan = [
            "extract_demographics",
            "extract_diagnoses",
            "extract_hospital_course",
            "extract_procedures",
            "extract_admission_medications",
            "extract_discharge_medications",
            "reconcile_medications",
            "detect_conflicts",
            "check_pending_results",
            "apply_safety_guardrail",
            "format_output"
        ]

    state.plan = plan
    state.current_task = plan[0] if plan else "format_output"

    print(f"[PLANNER] Plan: {plan}")
    print(f"[PLANNER] Next task: {state.current_task}")

    state.trace.append({
        "step": state.step_count,
        "node": "planner",
        "result": f"plan generated with {len(plan)} tasks",
        "next_task": state.current_task
    })

    state.step_count += 1
    return state


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────

def _format_raw_text(raw_text: dict[str, str]) -> str:
    """Format raw extracted text for the LLM prompt"""
    if not raw_text:
        return "No text extracted yet."
    parts = []
    for filename, text in raw_text.items():
        # Truncate to avoid token overflow — first 3000 chars per file
        preview = text[:3000] + "..." if len(text) > 3000 else text
        parts.append(f"--- {filename} ---\n{preview}")
    return "\n\n".join(parts)
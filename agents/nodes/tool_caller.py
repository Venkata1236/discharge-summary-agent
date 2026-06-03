import json
import anthropic
from agents.state import AgentState
from tools.drug_interaction import check_drug_interactions
from tools.flag_review import flag_for_review
from tools.pending_checker import check_pending_results


# ─────────────────────────────────────────────
# CLIENT — created once at module level
# ─────────────────────────────────────────────

client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# TOOL CALLER NODE
# ─────────────────────────────────────────────

def tool_caller_node(state: AgentState) -> AgentState:
    """
    Agent decides which tools to call based on current state.
    Tools are mock implementations — but agent decides when to call them.
    This demonstrates real tool-use judgment, not hardcoded calls.
    """

    state.trace.append({
        "step": state.step_count,
        "node": "tool_caller",
        "action": "deciding which tools to call",
    })

    print(f"[TOOL CALLER] Evaluating tool calls...")

    # Build context for tool decision
    flags = state.summary.flags
    conflicts = state.summary.conflicts
    discharge_meds = [m.model_dump() for m in state.summary.discharge_medications]
    pending = state.summary.pending_results

    prompt = f"""
You are a clinical AI agent deciding which tools to call.

CURRENT FLAGS:
{json.dumps(flags, indent=2)}

CURRENT CONFLICTS:
{json.dumps(conflicts, indent=2)}

DISCHARGE MEDICATIONS:
{json.dumps(discharge_meds, indent=2)}

PENDING RESULTS:
{json.dumps(pending, indent=2)}

Available tools:
1. check_drug_interactions — call when patient has 3+ discharge medications
2. flag_for_review         — call when there are unresolved conflicts or unexplained flags
3. check_pending_results   — call when pending results list is not empty

Decide which tools to call. Return ONLY valid JSON:
{{
    "tools_to_call": [
        {{
            "tool": "tool_name",
            "reason": "why you are calling this tool"
        }}
    ]
}}

If no tools are needed, return:
{{
    "tools_to_call": []
}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        tools_to_call = result.get("tools_to_call", [])
        print(f"[TOOL CALLER] Agent decided to call {len(tools_to_call)} tool(s)")

        # ── Execute each tool the agent decided to call ──
        for tool_call in tools_to_call:
            tool_name = tool_call.get("tool")
            reason = tool_call.get("reason", "")

            print(f"[TOOL CALLER] Calling: {tool_name} — Reason: {reason}")

            state.trace.append({
                "step": state.step_count,
                "node": "tool_caller",
                "action": f"calling tool: {tool_name}",
                "reason": reason
            })

            # ── Drug interaction check ──
            if tool_name == "check_drug_interactions":
                med_names = [
                    m.name for m in state.summary.discharge_medications
                ]
                tool_result = check_drug_interactions(med_names)
                state.tool_results.append({
                    "tool": "check_drug_interactions",
                    "input": med_names,
                    "result": tool_result
                })
                if tool_result.get("interactions"):
                    for interaction in tool_result["interactions"]:
                        flag = f"DRUG INTERACTION ALERT - {interaction} — Clinician Review Required"
                        state.summary.flags.append(flag)
                        print(f"[TOOL CALLER] ⚠ {flag}")

            # ── Flag for clinician review ──
            elif tool_name == "flag_for_review":
                tool_result = flag_for_review(
                    flags=state.summary.flags,
                    conflicts=state.summary.conflicts
                )
                state.tool_results.append({
                    "tool": "flag_for_review",
                    "input": {"flags": flags, "conflicts": conflicts},
                    "result": tool_result
                })
                print(f"[TOOL CALLER] ✓ Flagged for review: {tool_result.get('message')}")

            # ── Pending result checker ──
            elif tool_name == "check_pending_results":
                tool_result = check_pending_results(
                    pending=state.summary.pending_results
                )
                state.tool_results.append({
                    "tool": "check_pending_results",
                    "input": state.summary.pending_results,
                    "result": tool_result
                })
                if tool_result.get("critical_pending"):
                    for item in tool_result["critical_pending"]:
                        flag = f"CRITICAL PENDING RESULT - {item} — Clinician Review Required"
                        state.summary.flags.append(flag)
                        print(f"[TOOL CALLER] ⚠ {flag}")

            else:
                print(f"[TOOL CALLER] Unknown tool: {tool_name} — skipping")

            state.trace.append({
                "step": state.step_count,
                "node": "tool_caller",
                "result": f"tool {tool_name} completed",
            })

    except Exception as e:
        print(f"[TOOL CALLER] ✗ Failed: {e}")
        state.errors.append(f"tool_caller failed: {e}")

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
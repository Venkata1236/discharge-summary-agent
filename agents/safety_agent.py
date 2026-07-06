from agents.state import AgentState
from agents.nodes.conflict_detector import conflict_detector_node
from agents.nodes.tool_caller import tool_caller_node
from agents.nodes.safety_guardrail import safety_guardrail_node


# ─────────────────────────────────────────────
# SAFETY AGENT
# ─────────────────────────────────────────────
#
# Owns final validation across everything the other 3 agents produced.
# Runs, in order: conflict detection (cross-document contradictions),
# tool calling (drug interactions, pending results, escalation), then
# the deterministic safety guardrail. None of this logic is rewritten —
# these are the same tested node functions, just sequenced here instead
# of via the planner/router.
# ─────────────────────────────────────────────

class SafetyAgent:
    def run(self, state: AgentState) -> AgentState:
        print("[SAFETY AGENT] Detecting cross-document conflicts...")
        state = conflict_detector_node(state)

        print("[SAFETY AGENT] Evaluating tool calls...")
        state = tool_caller_node(state)

        print("[SAFETY AGENT] Running final safety guardrail...")
        state = safety_guardrail_node(state)

        print("[SAFETY AGENT] ✓ Done")
        return state
from agents.state import AgentState
from agents.narrative_agent import NarrativeAgent
from agents.medication_agent import MedicationAgent
from agents.lab_agent import LabAgent
from agents.safety_agent import SafetyAgent
from agents.nodes.output_formatter import output_formatter_node


# ─────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────
#
# Replaces the LangGraph planner/router loop with a fixed sequence of
# 4 domain-specialized agents. Each agent wraps and calls the existing,
# already-tested node logic internally — nothing from agents/nodes/ is
# rewritten here, just reorganized by clinical domain.
#
# Tradeoff worth being upfront about: the old planner.py dynamically
# re-planned after every step, which made this a genuine agent loop
# rather than a fixed pipeline. This orchestrator is NOT dynamic —
# it always runs Narrative -> Medication -> Lab -> Safety in that
# fixed order. What's gained is clear separation of concerns per
# clinical domain; what's given up is runtime re-planning.
# ─────────────────────────────────────────────

def run_orchestrator(state: AgentState) -> AgentState:
    print(f"\n{'='*60}")
    print(f"  MULTI-AGENT ORCHESTRATOR")
    print(f"{'='*60}\n")

    print("[ORCHESTRATOR] Dispatching Narrative Agent...")
    state = NarrativeAgent().run(state)

    print("[ORCHESTRATOR] Dispatching Medication Agent...")
    state = MedicationAgent().run(state)

    print("[ORCHESTRATOR] Dispatching Lab Agent...")
    state = LabAgent().run(state)

    print("[ORCHESTRATOR] Dispatching Safety Agent...")
    state = SafetyAgent().run(state)

    print("[ORCHESTRATOR] All agents complete — formatting output...")
    state = output_formatter_node(state)

    return state
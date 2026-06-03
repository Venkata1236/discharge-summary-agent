from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes.planner import planner_node
from agents.nodes.extractor import extractor_node
from agents.nodes.conflict_detector import conflict_detector_node
from agents.nodes.med_reconciliation import med_reconciliation_node
from agents.nodes.tool_caller import tool_caller_node
from agents.nodes.safety_guardrail import safety_guardrail_node
from agents.nodes.output_formatter import output_formatter_node


# ─────────────────────────────────────────────
# ROUTING LOGIC
# ─────────────────────────────────────────────

def route_task(state: AgentState) -> str:
    """
    Router — reads current_task from state and
    decides which node to call next.
    Also enforces the hard step cap.
    """

    # ── Hard step cap — never run forever ──
    if state.step_count >= state.max_steps:
        print(f"\n[GRAPH] ⚠ Step cap reached ({state.max_steps}) — forcing output")
        return "safety_guardrail"

    # ── Agent complete ──
    if state.is_complete:
        return END

    task = state.current_task

    # ── Extraction tasks → extractor node ──
    if task in [
        "extract_demographics",
        "extract_diagnoses",
        "extract_hospital_course",
        "extract_procedures",
        "extract_admission_medications",
        "extract_discharge_medications",
    ]:
        return "extractor"

    # ── Reconciliation ──
    elif task == "reconcile_medications":
        return "med_reconciliation"

    # ── Conflict detection ──
    elif task == "detect_conflicts":
        return "conflict_detector"

    # ── Tool calls ──
    elif task in [
        "call_drug_interaction_tool",
        "call_flag_review_tool",
        "call_pending_checker_tool",
        "check_pending_results",
    ]:
        return "tool_caller"

    # ── Safety guardrail ──
    elif task == "apply_safety_guardrail":
        return "safety_guardrail"

    # ── Output ──
    elif task == "format_output":
        return "output_formatter"

    # ── Unknown task — replan ──
    else:
        print(f"[GRAPH] Unknown task '{task}' — replanning")
        return "planner"


def should_end(state: AgentState) -> str:
    """Check if agent has completed"""
    if state.is_complete:
        return END
    return "router"


# ─────────────────────────────────────────────
# GRAPH BUILDER
# ─────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Builds and compiles the LangGraph agent.
    Flow:
      ingestion (handled in main.py)
        → planner
          → router
            → extractor / conflict_detector /
              med_reconciliation / tool_caller /
              safety_guardrail / output_formatter
                → loop back to router
                  → END when complete
    """

    graph = StateGraph(AgentState)

    # ── Add nodes ──
    graph.add_node("planner", planner_node)
    graph.add_node("extractor", extractor_node)
    graph.add_node("conflict_detector", conflict_detector_node)
    graph.add_node("med_reconciliation", med_reconciliation_node)
    graph.add_node("tool_caller", tool_caller_node)
    graph.add_node("safety_guardrail", safety_guardrail_node)
    graph.add_node("output_formatter", output_formatter_node)

    # ── Entry point ──
    graph.set_entry_point("planner")

    # ── Planner → router ──
    graph.add_conditional_edges(
        "planner",
        route_task,
        {
            "extractor": "extractor",
            "conflict_detector": "conflict_detector",
            "med_reconciliation": "med_reconciliation",
            "tool_caller": "tool_caller",
            "safety_guardrail": "safety_guardrail",
            "output_formatter": "output_formatter",
            END: END
        }
    )

    # ── Every node loops back through router ──
    for node in [
        "extractor",
        "conflict_detector",
        "med_reconciliation",
        "tool_caller",
        "safety_guardrail",
    ]:
        graph.add_conditional_edges(
            node,
            route_task,
            {
                "planner": "planner",
                "extractor": "extractor",
                "conflict_detector": "conflict_detector",
                "med_reconciliation": "med_reconciliation",
                "tool_caller": "tool_caller",
                "safety_guardrail": "safety_guardrail",
                "output_formatter": "output_formatter",
                END: END
            }
        )

    # ── Output formatter → END ──
    graph.add_edge("output_formatter", END)

    return graph.compile()
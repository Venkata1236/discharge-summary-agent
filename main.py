import os
import sys
import argparse
from dotenv import load_dotenv

from ingestion.pdf_loader import load_patient_pdfs
from agents.state import AgentState, DischargeSummary
from agents.graph import build_graph


# ─────────────────────────────────────────────
# LOAD ENV
# ─────────────────────────────────────────────

load_dotenv()


# ─────────────────────────────────────────────
# ARGUMENT PARSER
# ─────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Discharge Summary Agent — generates structured discharge summaries from patient PDFs"
    )
    parser.add_argument(
        "--patient",
        type=str,
        required=True,
        help="Path to patient folder containing PDF files. Example: data/patients/patient_2"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=25,
        help="Maximum agent steps before forced termination (default: 25)"
    )
    return parser.parse_args()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    args = parse_args()

    # ── Validate patient folder ──
    if not os.path.exists(args.patient):
        print(f"[ERROR] Patient folder not found: {args.patient}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  DISCHARGE SUMMARY AGENT")
    print(f"{'='*60}")
    print(f"  Patient folder : {args.patient}")
    print(f"  Max steps      : {args.max_steps}")
    print(f"{'='*60}\n")

    # ── Step 1: Ingest PDFs ──
    print("[MAIN] Starting PDF ingestion...")
    raw_text = load_patient_pdfs(args.patient)

    if not raw_text:
        print("[ERROR] No text extracted from PDFs — cannot proceed")
        sys.exit(1)

    print(f"[MAIN] ✓ Ingested {len(raw_text)} PDF file(s)\n")

    # ── Step 2: Build initial state ──
    initial_state = AgentState(
        patient_folder=args.patient,
        raw_text=raw_text,
        summary=DischargeSummary(),
        max_steps=args.max_steps
    )

    # ── Step 3: Build and run graph ──
    print("[MAIN] Building agent graph...")
    graph = build_graph()

    print("[MAIN] Running agent...\n")

    try:
        final_state = graph.invoke(initial_state)
        print(f"\n[MAIN] ✓ Agent completed in {final_state.step_count} steps")

    except Exception as e:
        print(f"\n[MAIN] ✗ Agent failed: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    main()
import json
import anthropic
from agents.state import AgentState, MISSING
from agents.config import MODEL_NAME
from ingestion.page_classifier import get_pages_for_task


# ─────────────────────────────────────────────
# CLIENT — created once at module level
# ─────────────────────────────────────────────

client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# LAB AGENT
# ─────────────────────────────────────────────
#
# Owns the lab/imaging domain — the one clinical area the original
# single-agent pipeline didn't extract at all. Follows the same
# LLM-call pattern as extractor.py: task-relevant pages only, strict
# JSON parsing, MISSING on anything not found, never fabricate.
# ─────────────────────────────────────────────

class LabAgent:
    def run(self, state: AgentState) -> AgentState:
        print("[LAB AGENT] Extracting lab and imaging results...")

        full_text = get_pages_for_task(state.classified_pages, "extract_lab_results")
        if not full_text:
            state.summary.flags.append(
                "LAB AGENT - No lab/imaging report pages found — verify with clinician"
            )
            print("[LAB AGENT] No relevant pages found — skipping")
            return state

        prompt = f"""
You are extracting lab and imaging results from a clinical document.

CLINICAL TEXT:
{full_text}

Extract all lab and imaging results, including values, units, reference
ranges, and whether each result is normal, abnormal, critical, or pending.
Base this ONLY on what is written in the document — do NOT infer or guess
a value that is not explicitly present.
If a sub-field is not found, use exactly: {MISSING}

Return ONLY valid JSON, no explanation:
{{
    "lab_results": [
        {{
            "test": "test name",
            "value": "result value",
            "unit": "unit",
            "reference_range": "normal range",
            "status": "normal | abnormal | critical | pending"
        }}
    ],
    "abnormal_flags": ["short description of each critical/abnormal result"]
}}
"""

        try:
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

            lab_results = result.get("lab_results", [])
            abnormal_flags = result.get("abnormal_flags", [])

            state.summary.lab_results = lab_results

            for flag in abnormal_flags:
                flag_msg = f"ABNORMAL LAB - {flag} — Clinician Review Required"
                state.summary.flags.append(flag_msg)
                print(f"[LAB AGENT] ⚠ {flag_msg}")

            print(f"[LAB AGENT] ✓ Extracted {len(lab_results)} lab result(s), {len(abnormal_flags)} flagged")

            state.trace.append({
                "step": state.step_count,
                "node": "lab_agent",
                "result": f"{len(lab_results)} lab result(s) extracted, {len(abnormal_flags)} abnormal"
            })

        except Exception as e:
            print(f"[LAB AGENT] ✗ Failed: {e}")
            state.errors.append(f"lab_agent failed: {e}")

        return state
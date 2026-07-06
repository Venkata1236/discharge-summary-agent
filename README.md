# Discharge Summary Agent

An agentic AI system that reads messy, real-world hospital records — scanned notes, drug charts, lab reports, handwritten nursing documentation — and turns them into a structured, standardized discharge summary draft for clinician review.

Hospitals generate a lot of inconsistent paperwork during a patient's stay. This agent reads all of it, extracts the key clinical facts, and assembles a proper discharge summary — without ever guessing. If something isn't clearly stated in the records, it's marked as missing instead of fabricated, and every medication change or cross-document contradiction is flagged before anything is considered ready for a doctor's sign-off.

---

## What It Does

- Ingests scanned, typed, and handwritten clinical PDFs using a hybrid extraction pipeline
- Classifies pages by clinical type and routes only relevant content to each extraction step
- Extracts patient demographics, diagnoses, hospital course, procedures, medications, and lab results
- Never fabricates a clinical fact — missing fields are explicitly marked `[MISSING - Clinician Review Required]`
- Reconciles admission vs. discharge medications using deterministic logic, flagging unexplained changes
- Detects contradictions between documents and surfaces both versions rather than picking one
- Calls tools only when needed — drug interaction checks, escalation, pending result review
- Runs through two interchangeable pipelines: a multi-agent orchestrator (default) or a dynamic LangGraph planner (legacy)
- Emits a full step-by-step trace and a numbered list of every flag requiring clinician review
- Always outputs a draft — never auto-finalizes a discharge summary

---

## Architecture

```
Patient PDFs
    ↓
[1] Ingestion (hybrid text extraction)
    ↓
[2] Page Classification (tag each page by type)
    ↓
[3] Agent Pipeline (two interchangeable implementations)
    ↓
[4] Output Formatter (structured JSON + flags + trace)
```

### Layer 1 — Ingestion

Each page runs through a three-tier extraction cascade:

1. **PyMuPDF** pulls the digital text layer directly — fast and free, used whenever the text passes a content quality check (not just a length check, since short text like `BP: 87/50` is clinically critical despite being tiny)
2. If that fails, a lightweight **handwriting pre-check** (Claude Vision, single yes/no call) decides whether the page is handwritten. If so, it skips OCR entirely and goes straight to full Vision transcription — Tesseract tends to produce garbled-but-plausible text on handwriting, which is more dangerous than a clean failure
3. Otherwise, **Tesseract OCR** runs first, falling back to full **Claude Vision** transcription only if OCR's output fails the same quality check

Every page is tagged with a marker (`[PAGE N - OCR]`, `[PAGE N - VISION]`, etc.) that the next layer depends on.

### Layer 2 — Page Classification

Each page is tagged with a clinical type — discharge summary, drug chart, lab report, nursing notes, consultation sheet, and so on — from a short preview. Downstream extraction steps request only the page types relevant to their task (medication extraction only needs drug charts, not the entire document), which replaced an earlier version that sent the full document to every single extraction call. If classification finds nothing relevant for a task, it falls back to sending everything rather than silently sending an empty string.

### Layer 3 — Agent Pipeline

Everything passes through a single state object (`AgentState`) holding raw text, classified pages, the working discharge summary, and a trace log. The summary itself uses explicit `MISSING` / `PENDING` sentinel values instead of `None` or empty strings — the core design principle throughout is **never fabricate, always mark the gap explicitly**.

Two pipelines are available, selected via a flag:

**Multi-agent orchestrator (default)**
A fixed sequence of four domain-specialized agents, each wrapping tested logic rather than reimplementing it:
- `NarrativeAgent` — demographics, diagnoses, hospital course, procedures
- `MedicationAgent` — extracts admission/discharge medications, then runs deterministic reconciliation
- `LabAgent` — extracts lab and imaging results
- `SafetyAgent` — runs conflict detection, tool calling, then the final deterministic safety guardrail

**Legacy LangGraph planner/router** (`--legacy-graph`)
The original design — an LLM planner re-plans after every step, and a router dispatches to whichever node the plan calls for next, looping until complete. This is dynamic and adaptive; the orchestrator is not — it always runs the same four steps in the same order. Both are kept intentionally: the orchestrator gives clean separation of concerns per clinical domain, the legacy graph gives genuine runtime re-planning. Neither is strictly better.

### The Core Safety Split — LLM vs. Deterministic

This is the most important design decision in the project, and it holds across both pipelines:

- **LLM-dependent**: anything that turns unstructured text into structured fields (demographics, diagnoses, medications, labs) — there's no deterministic way to parse free-text clinical notes
- **Zero-LLM, pure Python**: medication reconciliation (set comparison between medication lists) and the safety guardrail (field-presence checks, unconditional draft disclaimer) — these are the two places where correctness matters most and hallucination risk is least acceptable, which is also why they're the only nodes with dedicated unit tests

### Layer 4 — Output

Pure formatting, no LLM involved. Produces the final structured JSON (demographics, medications, conflicts, flags), prints the full step-by-step trace, and lists every flag requiring clinician sign-off before the summary could be used in practice.

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Agent orchestration | Custom multi-agent orchestrator + LangGraph (legacy) |
| LLM | Claude Sonnet (Anthropic API) |
| PDF ingestion | PyMuPDF + Tesseract OCR + Claude Vision |
| Validation | Pydantic |
| Config | python-dotenv |
| Tests | pytest |

---

## Project Structure

```
discharge-summary-agent/
├── main.py                          # Entry point — orchestrator by default, --legacy-graph for the LangGraph path
├── requirements.txt
├── .env.example
│
├── agents/
│   ├── state.py                     # AgentState + DischargeSummary models, MISSING/PENDING sentinels
│   ├── orchestrator.py              # Multi-agent coordinator (default pipeline)
│   ├── narrative_agent.py           # Demographics, diagnoses, hospital course, procedures
│   ├── medication_agent.py          # Medication extraction + reconciliation
│   ├── lab_agent.py                 # Lab and imaging result extraction
│   ├── safety_agent.py              # Conflict detection, tool calling, safety guardrail
│   ├── graph.py                     # Legacy LangGraph — router, step cap, conditional edges
│   └── nodes/
│       ├── planner.py               # Legacy — LLM-driven dynamic task planning
│       ├── extractor.py             # Legacy — field extraction, never fabricates
│       ├── conflict_detector.py     # Cross-note contradiction detection
│       ├── med_reconciliation.py    # Deterministic admission vs. discharge diff
│       ├── tool_caller.py           # Agent-decided tool invocation
│       ├── safety_guardrail.py      # No-fabrication enforcement (deterministic)
│       └── output_formatter.py      # Structured JSON + trace to terminal
│
├── tools/
│   ├── drug_interaction.py          # Drug interaction lookup with severity levels
│   ├── flag_review.py               # Clinician escalation tool
│   └── pending_checker.py           # Pending result checker
│
├── ingestion/
│   ├── pdf_loader.py                # Hybrid extraction orchestrator
│   ├── page_classifier.py           # Page type classification and task-based routing
│   ├── ocr_engine.py                # Tesseract with image preprocessing
│   └── vision_fallback.py           # Claude Vision transcription + handwriting pre-check
│
└── tests/
    ├── test_safety_guardrail.py
    ├── test_conflict_detector.py
    └── test_med_reconciliation.py
```

---

## Setup

**1. Clone the repo**

```bash
git clone https://github.com/Venkata1236/discharge-summary-agent.git
cd discharge-summary-agent
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

Mac/Linux:
```bash
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Install Tesseract (system-level)**

Windows — download the installer from:
https://github.com/UB-Mannheim/tesseract/wiki

**5. Install Poppler (system-level, required for PDF-to-image conversion)**

Windows — download from:
https://github.com/oschwartz10612/poppler-windows/releases

**6. Configure environment**

```bash
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=your_api_key_here
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

**7. Add patient PDFs**

```
data/
└── patients/
    ├── patient_1/
    │   └── *.pdf
    └── patient_2/
        └── *.pdf
```

---

## Run

**Default — multi-agent orchestrator**
```bash
python main.py --patient data/patients/patient_2
```

**Legacy — LangGraph planner/router**
```bash
python main.py --patient data/patients/patient_2 --legacy-graph
```

**Custom step cap (legacy pipeline only)**
```bash
python main.py --patient data/patients/patient_2 --legacy-graph --max-steps 30
```

---

## Sample Output

```
============================================================
  DISCHARGE SUMMARY AGENT
============================================================
  Patient folder : data/patients/patient_2
============================================================

[INGESTION] Processing: admission_note.pdf
[INGESTION] Page 1 → digital text layer
[INGESTION] Page 2 → handwriting detected, routing to Vision
[CLASSIFIER] Task 'extract_admission_medications' → 4 relevant page(s)

[NARRATIVE AGENT] Extracting demographics, diagnoses, hospital course...
[MEDICATION AGENT] Comparing admission vs. discharge meds (deterministic)...
[MEDICATION AGENT] ⚠ STOPPED: Metformin 500mg — Clinician Review Required
[LAB AGENT] Extracting lab and imaging results...
[SAFETY AGENT] ⚠ CONFLICT in 'allergies': 'NKDA' vs 'Penicillin allergy'
[SAFETY AGENT] 🚨 CRITICAL - Allergy status conflict — Clinician Review Required

============================================================
  DISCHARGE SUMMARY
============================================================
{
  "meta": {
    "status": "DRAFT - Clinician Review Required",
    "total_flags": 6
  },
  "patient_demographics": { "..." },
  ...
}
```

---

## Safety Design

Three layers enforce the no-fabrication rule:

**Layer 1 — Extraction**
Every extraction prompt explicitly instructs the model to return `[MISSING - Clinician Review Required]` for any field not found in the source document. Guessing is not permitted.

**Layer 2 — Conflict Detection**
When two documents disagree on the same fact, both versions are preserved and flagged. The system never picks one version over the other.

**Layer 3 — Safety Guardrail**
A deterministic final pass with no LLM involvement sweeps every field before output. Any empty, null, or blank field is replaced with `[MISSING - Clinician Review Required]`. This step runs on every execution path and cannot be bypassed — it always appends a `DRAFT ONLY` disclaimer to the output.

---

## Design Principles

- **Never fabricate.** Every field is either sourced from the documents or explicitly marked missing.
- **Deterministic where correctness matters most.** Medication reconciliation and the safety guardrail use plain Python, not an LLM — there's no acceptable hallucination risk in either.
- **Route, don't dump.** Extraction steps receive only the page types relevant to their task, not the entire document on every call.
- **Preserve contradictions, don't resolve them.** Conflicting information is surfaced with both versions and their sources, never silently picked between.
- **Always a draft.** No output is ever final. Every run ends with an explicit clinician sign-off requirement.

---

## Known Limitations and Future Improvements

- **Mock tools** — drug interaction lookup, escalation, and pending result checks are illustrative implementations. Production use would integrate a real source such as a DrugBank API or hospital EMR feed.
- **Fixed orchestrator sequence** — the multi-agent pipeline runs the same four steps in the same order every time, unlike the legacy planner which re-plans dynamically. A future version could combine both — specialized agents with dynamic sequencing.
- **No persistent storage** — output is terminal-only. A production version would log summaries with a full audit trail (who generated it, which pipeline version, what a clinician edited).
- **Page classification is preview-based** — pages are classified from a short text preview, which could misclassify unusually formatted documents. A production version might use full-page context or a fine-tuned classifier.

---

## Tests

```bash
pytest tests/ -v
```

Tests cover the deterministic components specifically — medication reconciliation and the safety guardrail — since these are the modules where correctness is most critical and easiest to verify without mocking an LLM.

---

## Author

Venkat Reddy
AI/ML Engineer
github.com/Venkata1236
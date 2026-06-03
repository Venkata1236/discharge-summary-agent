# Discharge Summary Agent

An agentic AI system that reads messy scanned clinical PDFs and produces
structured, safe discharge summary drafts for clinician review.

Built as a take-home assignment for Dscribe (Unriddle Technologies).

---

## Demo

> Agent running live on Patient 2 — flags conflicts, reconciles medications, enforces no-fabrication rule.

*(Loom link here after recording)*

---

## What It Does

- Ingests scanned clinical PDFs using a hybrid pipeline (PyMuPDF → Tesseract OCR → Claude Vision)
- Runs a LangGraph agent loop that plans, extracts, reconciles, and flags — step by step
- Never fabricates clinical facts — missing fields are explicitly marked
- Detects conflicts between notes and flags them without picking sides
- Reconciles admission vs discharge medications using deterministic Python logic
- Calls mock tools only when needed — drug interaction lookup, flag for review, pending checker
- Emits a full step-by-step agent trace alongside the discharge summary
- Enforces a hard 25-step cap — agent cannot run forever

---

## Architecture

**Step 1 — Ingestion**

Patient PDF folder is read page by page using a hybrid pipeline:
- PyMuPDF first — fast, works if digital text layer exists
- Tesseract OCR fallback — for printed scanned pages
- Claude Vision fallback — for handwritten nursing notes and messy charts

**Step 2 — Agent Loop (max 25 steps)**

The agent plans, executes, and re-plans after every step.

| Node | What It Does |
|------|-------------|
| Planner | LLM decides what to extract next — re-plans every step |
| Extractor | Fills demographics, diagnoses, meds, procedures, hospital course |
| Conflict Detector | Cross-checks all notes — flags contradictions, never picks sides |
| Med Reconciliation | Deterministic Python set logic — flags stopped, changed, added meds |
| Tool Caller | Agent decides when to call drug interaction, flag review, pending checker |
| Safety Guardrail | Deterministic — no LLM — missing fields get `[MISSING - Clinician Review Required]` |
| Output Formatter | Structured JSON discharge summary + full agent trace printed to terminal |

**Step 3 — Output**

Structured JSON discharge summary and step-by-step agent trace printed to terminal.

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Agent loop | LangGraph |
| LLM | Claude Sonnet `claude-sonnet-4-20250514` |
| PDF ingestion | PyMuPDF + Tesseract OCR + Claude Vision fallback |
| Validation | Pydantic |
| Config | python-dotenv |
| Tests | pytest |

---

## Project Structure

```
discharge-summary-agent/
├── main.py
├── requirements.txt
├── .env.example
├── agents/
│   ├── state.py
│   ├── graph.py
│   └── nodes/
│       ├── planner.py
│       ├── extractor.py
│       ├── conflict_detector.py
│       ├── med_reconciliation.py
│       ├── tool_caller.py
│       ├── safety_guardrail.py
│       └── output_formatter.py
├── tools/
│   ├── drug_interaction.py
│   ├── flag_review.py
│   └── pending_checker.py
├── ingestion/
│   ├── pdf_loader.py
│   ├── ocr_engine.py
│   └── vision_fallback.py
├── output/
│   ├── formatter.py
│   └── trace_logger.py
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

**2. Create and activate virtual environment**

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

**5. Configure environment**

```bash
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=your_api_key_here
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

**6. Add patient PDFs**

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

```bash
python main.py --patient data/patients/patient_2
```

```bash
python main.py --patient data/patients/patient_1
```

```bash
python main.py --patient data/patients/patient_2 --max-steps 30
```

---

## Sample Output

```
============================================================
  DISCHARGE SUMMARY AGENT
============================================================
  Patient folder : data/patients/patient_2
  Max steps      : 25
============================================================

[INGESTION] Processing: admission_note.pdf
[INGESTION] Page 1 → trying OCR
[INGESTION] Page 2 → Vision fallback
[INGESTION] ✓ Extracted 4821 chars

[PLANNER] Plan: ['extract_demographics', 'extract_diagnoses', ...]
[EXTRACTOR] Task: extract_demographics
[CONFLICT DETECTOR] ⚠ CONFLICT in 'age_sex': '45/M' vs '45/F'
[MED RECONCILIATION] ⚠ STOPPED: Metformin 500mg — Clinician Review Required
[TOOL CALLER] Calling: flag_for_review
[SAFETY GUARDRAIL] 🚨 CRITICAL - Allergy status unknown

============================================================
  DISCHARGE SUMMARY
============================================================
{
  "meta": {
    "status": "DRAFT - Clinician Review Required",
    "total_flags": 6
  },
  "patient_demographics": {
    "name": "...",
    "age_sex": "CONFLICT - Clinician Review Required"
  }
}
```

---

## Safety Design

Three layers enforce the no-fabrication rule:

**Layer 1 — Extraction**
The extractor prompt explicitly instructs the LLM to return
`[MISSING - Clinician Review Required]` for any field not found
in the source document. Guessing is not permitted.

**Layer 2 — Conflict Detection**
When two documents disagree on the same fact, both versions
are preserved and flagged. The system never picks one version
over the other.

**Layer 3 — Safety Guardrail**
A deterministic final node with no LLM sweeps every field before
output. Any empty or blank field is replaced with
`[MISSING - Clinician Review Required]`. This node runs on every
execution path including step-cap exits and cannot be bypassed.

---

## Known Limitations and Production Improvements

**1. Full text sent to each extraction call**

Current: all PDF pages are sent to every extractor call.

Production fix: a page classifier node routes only relevant
sections to each extractor — medication charts to med extractor only.

Impact: ~80% token reduction on large patient files.

**2. Planner sees truncated document preview**

Current: planner receives first 3000 chars per document.

Production fix: chunk-based retrieval where planner sees chunk
summaries and fetches relevant chunks on demand.

Impact: full document awareness regardless of file length.

**3. Conflict detector sends full raw text**

Current: full text sent for conflict detection.

Production fix: compare only pre-extracted field values and
their source snippets instead of entire documents.

Impact: ~95% token reduction with same detection quality.

**4. Mock tools**

Current: drug interaction, flag review, and pending checker
are mock implementations.

Production fix: integrate real clinical databases such as
DrugBank API, hospital EMR system, and lab result feeds.

**5. No persistent storage**

Current: output is terminal only.

Production fix: store summaries in PostgreSQL with full
audit trail — who generated, which version, clinician edits.

---

## Tests

```bash
pytest tests/ -v
```

---

## Author

Venkat Reddy
AI/ML Engineer
bommavaramvenkat2003@gmail.com
linkedin.com/in/venkatareddy1203
github.com/Venkata1236
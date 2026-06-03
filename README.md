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
- Calls mock tools (drug interaction lookup, flag for review, pending checker) only when needed
- Emits a full step-by-step agent trace alongside the discharge summary
- Enforces a hard 25-step cap — agent cannot run forever

---

## Architecture
Patient PDF folder
↓
PDF Ingestion (PyMuPDF → Tesseract OCR → Claude Vision fallback)
↓
Planner Node (LLM decides what to extract next — re-plans every step)
↓
┌─────────────────────────────────────────┐
│              Agent Loop                 │
│                                         │
│  Extractor Node                         │
│  → demographics, diagnoses, meds,       │
│    procedures, hospital course          │
│                                         │
│  Conflict Detector Node                 │
│  → cross-checks all notes               │
│  → flags contradictions, never picks    │
│                                         │
│  Med Reconciliation Node                │
│  → deterministic Python set logic       │
│  → flags stopped/changed/added meds     │
│                                         │
│  Tool Caller Node                       │
│  → drug interaction lookup (mock)       │
│  → flag for clinician review (mock)     │
│  → pending result checker (mock)        │
│                                         │
│  Hard step cap: 25 steps → force exit   │
└─────────────────────────────────────────┘
↓
Safety Guardrail Node
→ deterministic — no LLM
→ missing fields → [MISSING - Clinician Review Required]
→ never guesses, never fills blanks
↓
Output Formatter Node
→ structured JSON discharge summary
→ full agent trace
→ flags requiring clinician review

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Agent loop | LangGraph |
| LLM | Claude Sonnet (`claude-sonnet-4-20250514`) |
| PDF ingestion | PyMuPDF + Tesseract OCR + Claude Vision fallback |
| Validation | Pydantic |
| Config | python-dotenv |
| Tests | pytest |

---

## Project Structure
discharge-summary-agent/
│
├── main.py                          # Entry point
├── requirements.txt
├── .env.example
│
├── agents/
│   ├── state.py                     # AgentState + DischargeSummary Pydantic models
│   ├── graph.py                     # LangGraph graph — nodes, edges, router, step cap
│   └── nodes/
│       ├── planner.py               # LLM-driven dynamic task planning
│       ├── extractor.py             # Field extraction — never fabricates
│       ├── conflict_detector.py     # Cross-note contradiction detection
│       ├── med_reconciliation.py    # Deterministic admission vs discharge diff
│       ├── tool_caller.py           # Agent-decided tool invocation
│       ├── safety_guardrail.py      # No-fabrication enforcement
│       └── output_formatter.py      # Structured JSON + trace to terminal
│
├── tools/
│   ├── drug_interaction.py          # Mock drug interaction lookup
│   ├── flag_review.py               # Mock escalation tool
│   └── pending_checker.py           # Mock pending result checker
│
├── ingestion/
│   ├── pdf_loader.py                # Hybrid extraction orchestrator
│   ├── ocr_engine.py                # Tesseract with image preprocessing
│   └── vision_fallback.py           # Claude Vision for handwritten pages
│
├── output/
│   ├── formatter.py                 # Output structure
│   └── trace_logger.py              # Step trace
│
└── tests/
├── test_safety_guardrail.py
├── test_conflict_detector.py
└── test_med_reconciliation.py

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Venkata1236/discharge-summary-agent.git
cd discharge-summary-agent
```

### 2. Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract (system-level)

Windows: download installer from
https://github.com/UB-Mannheim/tesseract/wiki

### 5. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
ANTHROPIC_API_KEY=your_api_key_here
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

### 6. Add patient PDFs
data/
└── patients/
├── patient_1/
│   ├── admission_note.pdf
│   └── discharge_note.pdf
└── patient_2/
├── admission_note.pdf
└── discharge_note.pdf

---

## Run

```bash
# Patient 2
python main.py --patient data/patients/patient_2

# Patient 1
python main.py --patient data/patients/patient_1

# Custom step cap
python main.py --patient data/patients/patient_2 --max-steps 30
```

---

## Sample Output
============================================================
DISCHARGE SUMMARY AGENT
Patient folder : data/patients/patient_2
Max steps      : 25
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
{
"meta": {
"status": "DRAFT - Clinician Review Required",
"total_flags": 6
},
"patient_demographics": {
"name": "...",
"age_sex": "CONFLICT - '45/M' vs '45/F' - Clinician Review Required"
},
...
}

---

## Safety Design

The system enforces three layers of safety:

**Layer 1 — Extraction**
The extractor prompt explicitly instructs the LLM to return
`[MISSING - Clinician Review Required]` for any field not found
in the source document. Guessing is not permitted.

**Layer 2 — Conflict Detection**
When two documents disagree on the same fact, both versions
are preserved and flagged. The system never picks one version
over the other.

**Layer 3 — Safety Guardrail**
A deterministic final node (no LLM) sweeps every field before
output. Any empty, None, or blank field is replaced with
`[MISSING - Clinician Review Required]`. This node cannot be
bypassed — it runs on every execution path including step-cap exits.

---

## Known Limitations & Production Improvements

### 1. Full text sent to each extraction call
**Current:** all PDF pages are sent to every extractor call.
**Production fix:** a page classifier node routes only relevant
sections to each extractor (e.g. medication charts → med extractor only).
**Impact:** ~80% token reduction on large patient files.

### 2. Planner sees truncated document preview
**Current:** planner receives first 3000 chars per document.
**Production fix:** chunk-based retrieval — planner sees chunk
summaries and fetches relevant chunks on demand (mini-RAG pipeline).
**Impact:** planner has full document awareness regardless of length.

### 3. Conflict detector sends full raw text
**Current:** full text sent for conflict detection.
**Production fix:** compare only pre-extracted field values and
their source snippets — not the entire document.
**Impact:** ~95% token reduction, same detection quality.

### 4. Mock tools
**Current:** drug interaction, flag review, and pending checker
are mock implementations.
**Production fix:** integrate real clinical databases
(DrugBank API, hospital EMR system, lab result feeds).

### 5. No persistent storage
**Current:** output is terminal only.
**Production fix:** store summaries in PostgreSQL with full
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
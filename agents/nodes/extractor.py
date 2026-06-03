import json
import anthropic
from agents.state import AgentState, Medication, MISSING, PENDING


# ─────────────────────────────────────────────
# CLIENT — created once at module level
# ─────────────────────────────────────────────

client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# EXTRACTOR NODE
# ─────────────────────────────────────────────

def extractor_node(state: AgentState) -> AgentState:
    """
    Extracts clinical fields from raw text based on current_task.
    Never guesses — if data is not found, field stays MISSING.
    """

    task = state.current_task
    full_text = _combine_raw_text(state.raw_text)

    state.trace.append({
        "step": state.step_count,
        "node": "extractor",
        "action": f"extracting: {task}",
        "input": f"{len(full_text)} chars of raw text"
    })

    print(f"[EXTRACTOR] Task: {task}")

    if task == "extract_demographics":
        state = _extract_demographics(state, full_text)

    elif task == "extract_diagnoses":
        state = _extract_diagnoses(state, full_text)

    elif task == "extract_hospital_course":
        state = _extract_hospital_course(state, full_text)

    elif task == "extract_procedures":
        state = _extract_procedures(state, full_text)

    elif task == "extract_admission_medications":
        state = _extract_admission_medications(state, full_text)

    elif task == "extract_discharge_medications":
        state = _extract_discharge_medications(state, full_text)

    else:
        print(f"[EXTRACTOR] Unknown task: {task} — skipping")

    # Advance to next task in plan
    state = _advance_plan(state)
    state.step_count += 1
    return state


# ─────────────────────────────────────────────
# EXTRACTION FUNCTIONS
# ─────────────────────────────────────────────

def _extract_demographics(state: AgentState, text: str) -> AgentState:
    prompt = f"""
You are extracting patient demographics from a clinical document.

CLINICAL TEXT:
{text}

Extract the following fields exactly as they appear in the document.
If a field is not found, return exactly: {MISSING}
If a field is pending, return exactly: {PENDING}

Return ONLY valid JSON, no explanation:
{{
    "patient_name": "...",
    "patient_id": "...",
    "age_sex": "...",
    "dob": "...",
    "admission_date": "...",
    "discharge_date": "...",
    "consultant": "...",
    "ward": "...",
    "allergies": "...",
    "discharge_condition": "..."
}}
"""
    result = _call_llm(prompt)
    if result:
        s = state.summary
        s.patient_name = result.get("patient_name", MISSING)
        s.patient_id = result.get("patient_id", MISSING)
        s.age_sex = result.get("age_sex", MISSING)
        s.dob = result.get("dob", MISSING)
        s.admission_date = result.get("admission_date", MISSING)
        s.discharge_date = result.get("discharge_date", MISSING)
        s.consultant = result.get("consultant", MISSING)
        s.ward = result.get("ward", MISSING)
        s.allergies = result.get("allergies", MISSING)
        s.discharge_condition = result.get("discharge_condition", MISSING)

        state.trace.append({
            "step": state.step_count,
            "node": "extractor",
            "result": "demographics extracted",
            "data": result
        })
    return state


def _extract_diagnoses(state: AgentState, text: str) -> AgentState:
    prompt = f"""
You are extracting diagnoses from a clinical document.

CLINICAL TEXT:
{text}

Extract the following fields exactly as they appear.
If not found, return exactly: {MISSING}

Return ONLY valid JSON:
{{
    "principal_diagnosis": "...",
    "secondary_diagnoses": ["...", "..."]
}}
"""
    result = _call_llm(prompt)
    if result:
        state.summary.principal_diagnosis = result.get("principal_diagnosis", MISSING)
        state.summary.secondary_diagnoses = result.get("secondary_diagnoses", [])

        state.trace.append({
            "step": state.step_count,
            "node": "extractor",
            "result": "diagnoses extracted",
            "data": result
        })
    return state


def _extract_hospital_course(state: AgentState, text: str) -> AgentState:
    prompt = f"""
You are extracting the hospital course from a clinical document.

CLINICAL TEXT:
{text}

Summarize the hospital course — what happened during the admission, 
key clinical events, treatments given, response to treatment.
Base this ONLY on what is written in the document.
Do NOT add any information not present in the text.
If not found, return exactly: {MISSING}

Return ONLY valid JSON:
{{
    "hospital_course": "..."
}}
"""
    result = _call_llm(prompt)
    if result:
        state.summary.hospital_course = result.get("hospital_course", MISSING)

        state.trace.append({
            "step": state.step_count,
            "node": "extractor",
            "result": "hospital course extracted"
        })
    return state


def _extract_procedures(state: AgentState, text: str) -> AgentState:
    prompt = f"""
You are extracting procedures from a clinical document.

CLINICAL TEXT:
{text}

List all procedures performed during the admission exactly as mentioned.
If none found, return empty list.

Return ONLY valid JSON:
{{
    "procedures": ["...", "..."]
}}
"""
    result = _call_llm(prompt)
    if result:
        state.summary.procedures = result.get("procedures", [])

        state.trace.append({
            "step": state.step_count,
            "node": "extractor",
            "result": "procedures extracted",
            "data": result
        })
    return state


def _extract_admission_medications(state: AgentState, text: str) -> AgentState:
    prompt = f"""
You are extracting admission medications from a clinical document.

CLINICAL TEXT:
{text}

Extract ALL medications the patient was on at the time of admission.
For each medication extract: name, dose, frequency, route, duration.
If a sub-field is not found, use exactly: {MISSING}

Return ONLY valid JSON:
{{
    "admission_medications": [
        {{
            "name": "...",
            "dose": "...",
            "frequency": "...",
            "route": "...",
            "duration": "..."
        }}
    ]
}}
"""
    result = _call_llm(prompt)
    if result:
        raw_meds = result.get("admission_medications", [])
        state.summary.admission_medications = [
            Medication(**med) for med in raw_meds
        ]

        state.trace.append({
            "step": state.step_count,
            "node": "extractor",
            "result": f"{len(raw_meds)} admission medications extracted"
        })
    return state


def _extract_discharge_medications(state: AgentState, text: str) -> AgentState:
    prompt = f"""
You are extracting discharge medications from a clinical document.

CLINICAL TEXT:
{text}

Extract ALL medications the patient is being discharged with.
For each medication extract: name, dose, frequency, route, duration.
If a sub-field is not found, use exactly: {MISSING}

Return ONLY valid JSON:
{{
    "discharge_medications": [
        {{
            "name": "...",
            "dose": "...",
            "frequency": "...",
            "route": "...",
            "duration": "..."
        }}
    ]
}}
"""
    result = _call_llm(prompt)
    if result:
        raw_meds = result.get("discharge_medications", [])
        state.summary.discharge_medications = [
            Medication(**med) for med in raw_meds
        ]

        state.trace.append({
            "step": state.step_count,
            "node": "extractor",
            "result": f"{len(raw_meds)} discharge medications extracted"
        })
    return state


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _call_llm(prompt: str) -> dict | None:
    """Call Claude and parse JSON response safely"""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[EXTRACTOR] LLM call failed: {e}")
        return None


def _combine_raw_text(raw_text: dict[str, str]) -> str:
    """Combine all extracted PDF text into one string for the LLM"""
    parts = []
    for filename, text in raw_text.items():
        parts.append(f"=== {filename} ===\n{text}")
    return "\n\n".join(parts)


def _advance_plan(state: AgentState) -> AgentState:
    """Remove completed task from plan and set next current_task"""
    if state.plan:
        state.plan.pop(0)
    state.current_task = state.plan[0] if state.plan else "format_output"
    return state
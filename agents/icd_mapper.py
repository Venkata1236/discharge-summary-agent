import json
import anthropic
from agents.state import MISSING
from agents.config import MODEL_NAME


client = anthropic.Anthropic()


def map_to_icd10(diagnosis_text: str) -> dict:
    """
    Maps a free-text diagnosis to the most likely ICD-10 code.
    Uses LLM recall, not a validated code lookup — see README
    known-limitations note. Returns MISSING if too ambiguous to map.
    """
    if not diagnosis_text or diagnosis_text == MISSING:
        return {"code": MISSING, "description": MISSING, "confidence": 0.0}

    prompt = f"""
You are a clinical coding specialist mapping diagnoses to ICD-10 codes.

DIAGNOSIS TEXT: {diagnosis_text}

Return the single most appropriate ICD-10 code for this diagnosis.
If the diagnosis is too vague or ambiguous to map confidently, return the code as {MISSING}.

Return ONLY valid JSON:
{{
    "icd10_code": "code or {MISSING}",
    "icd10_description": "official ICD-10 description",
    "confidence": 0.0
}}
"""
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return {
            "code": result.get("icd10_code", MISSING),
            "description": result.get("icd10_description", MISSING),
            "confidence": result.get("confidence", 0.0)
        }
    except Exception as e:
        print(f"[ICD MAPPER] Failed: {e}")
        return {"code": MISSING, "description": MISSING, "confidence": 0.0}
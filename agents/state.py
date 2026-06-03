from typing import Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

MISSING = "[MISSING - Clinician Review Required]"
PENDING = "[PENDING - Awaiting Result]"


# ─────────────────────────────────────────────
# SUB-MODELS
# ─────────────────────────────────────────────

class Medication(BaseModel):
    name: str = MISSING
    dose: str = MISSING
    frequency: str = MISSING
    duration: str = MISSING
    route: str = MISSING


class MedicationChange(BaseModel):
    medication: str
    change_type: str          # "added" | "stopped" | "dose_changed" | "unexplained"
    note: str = MISSING


# ─────────────────────────────────────────────
# DISCHARGE SUMMARY — final structured output
# ─────────────────────────────────────────────

class DischargeSummary(BaseModel):
    # Demographics
    patient_name: str = MISSING
    patient_id: str = MISSING
    age_sex: str = MISSING
    dob: str = MISSING

    # Admission info
    admission_date: str = MISSING
    discharge_date: str = MISSING
    consultant: str = MISSING
    ward: str = MISSING

    # Diagnoses
    principal_diagnosis: str = MISSING
    secondary_diagnoses: list[str] = Field(default_factory=list)

    # Clinical course
    hospital_course: str = MISSING
    procedures: list[str] = Field(default_factory=list)

    # Medications
    admission_medications: list[Medication] = Field(default_factory=list)
    discharge_medications: list[Medication] = Field(default_factory=list)
    medication_changes: list[MedicationChange] = Field(default_factory=list)

    # Safety
    allergies: str = MISSING
    discharge_condition: str = MISSING

    # Follow-up
    follow_up_instructions: list[str] = Field(default_factory=list)
    pending_results: list[str] = Field(default_factory=list)

    # Agent-generated flags
    flags: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────
# AGENT STATE — passed between every node
# ─────────────────────────────────────────────

class AgentState(BaseModel):
    # Input
    patient_folder: str

    # Ingestion output — {filename: extracted_text}
    raw_text: dict[str, str] = Field(default_factory=dict)

    # Working summary — updated by each node
    summary: DischargeSummary = Field(default_factory=DischargeSummary)

    # Agent loop control
    step_count: int = 0
    max_steps: int = 25
    is_complete: bool = False

    # Planner output
    plan: list[str] = Field(default_factory=list)
    current_task: str = ""

    # Tool results from tool_caller node
    tool_results: list[dict] = Field(default_factory=list)

    # Step-by-step trace
    trace: list[dict] = Field(default_factory=list)

    # Errors
    errors: list[str] = Field(default_factory=list)
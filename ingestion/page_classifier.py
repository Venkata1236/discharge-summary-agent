import anthropic
from agents.config import MODEL_NAME


# ─────────────────────────────────────────────
# CLIENT — created once at module level
# ─────────────────────────────────────────────

client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# PAGE TYPES
# ─────────────────────────────────────────────

PAGE_TYPES = [
    "discharge_summary",
    "admission_note",
    "progress_note",
    "lab_report",
    "drug_chart",
    "nursing_notes",
    "consultation_sheet",
    "procedure_chart",
    "imaging_report",
    "other"
]


# ─────────────────────────────────────────────
# CLASSIFY ALL PAGES
# ─────────────────────────────────────────────

def classify_pages(raw_text: dict[str, str]) -> dict[str, list[str]]:
    """
    Classify each page of every ingested document by clinical page type.
    Returns {page_type: [page_text, page_text, ...]}

    Pages are split on the "[PAGE N - ..." markers inserted by
    ingestion/pdf_loader.py during extraction.
    """
    classified = {page_type: [] for page_type in PAGE_TYPES}

    for filename, full_text in raw_text.items():
        if not full_text:
            continue

        # Split on the page markers pdf_loader.py inserts between pages
        pages = full_text.split("\n\n[PAGE ")
        for i, page_chunk in enumerate(pages):
            if not page_chunk.strip():
                continue

            # Restore the marker prefix lost on every page but the first,
            # since it was consumed as the split delimiter
            if i > 0:
                page_chunk = "[PAGE " + page_chunk

            page_type = _classify_single_page(page_chunk[:500])
            classified[page_type].append(page_chunk)

    print(f"[CLASSIFIER] Page classification complete:")
    for ptype, pages in classified.items():
        if pages:
            print(f"[CLASSIFIER]   {ptype}: {len(pages)} page(s)")

    return classified


def _classify_single_page(page_preview: str) -> str:
    """Classify a single page based on a short preview of its content"""
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": f"""Classify this clinical document page into exactly one category.

Page content (preview):
{page_preview}

Categories: discharge_summary, admission_note, progress_note, lab_report,
drug_chart, nursing_notes, consultation_sheet, procedure_chart, imaging_report, other

Return ONLY the category name, nothing else."""
            }]
        )
        result = response.content[0].text.strip().lower()
        if result in PAGE_TYPES:
            return result
        return "other"
    except Exception as e:
        print(f"[CLASSIFIER] Page classification failed, defaulting to 'other': {e}")
        return "other"


# ─────────────────────────────────────────────
# GET RELEVANT PAGES FOR A GIVEN TASK
# ─────────────────────────────────────────────

def get_pages_for_task(classified: dict[str, list[str]], task: str) -> str:
    """
    Return only the relevant pages for a given extraction task, instead of
    sending the full combined document to every LLM call.
    """
    task_to_pages = {
        "extract_demographics":          ["discharge_summary", "admission_note"],
        "extract_diagnoses":             ["discharge_summary", "admission_note", "consultation_sheet"],
        "extract_hospital_course":       ["discharge_summary", "progress_note", "consultation_sheet"],
        "extract_procedures":            ["discharge_summary", "procedure_chart", "nursing_notes"],
        "extract_admission_medications": ["drug_chart", "admission_note"],
        "extract_discharge_medications": ["discharge_summary", "drug_chart"],
        "detect_conflicts":              ["discharge_summary", "lab_report", "admission_note"],
        "check_pending_results":         ["lab_report", "discharge_summary"],
    }

    relevant_types = task_to_pages.get(task, PAGE_TYPES)
    relevant_pages = []

    for page_type in relevant_types:
        relevant_pages.extend(classified.get(page_type, []))

    combined = "\n\n".join(relevant_pages)

    # Fallback: if classification found nothing relevant (e.g. everything
    # landed in "other", or classification failed), fall back to ALL pages
    # rather than silently sending an empty string to the extractor.
    if not combined:
        print(f"[CLASSIFIER] No relevant pages found for '{task}' — falling back to all pages")
        all_pages = [p for pages in classified.values() for p in pages]
        combined = "\n\n".join(all_pages)

    print(f"[CLASSIFIER] Task '{task}' → {len(relevant_pages)} relevant page(s) — {len(combined)} chars")
    return combined
import fitz  # PyMuPDF
from pathlib import Path
from ingestion.ocr_engine import run_ocr
from ingestion.vision_fallback import run_vision


# ─────────────────────────────────────────────
# TEXT QUALITY CHECK
# ─────────────────────────────────────────────

def is_meaningful_text(text: str) -> bool:
    """
    Check if extracted text is actually useful clinical content.
    Character count alone is unreliable — short text can be critical.
    e.g. 'BP: 87/50' is only 10 chars but life-critical.
    """
    if not text or len(text.strip()) == 0:
        return False

    # Must have at least 3 real words (not just symbols or numbers)
    words = [w for w in text.split() if w.isalpha() and len(w) > 1]
    if len(words) < 3:
        return False

    # Reject garbled OCR garbage characters
    garbage_ratio = sum(1 for c in text if c in "█▓▒░|}{~^") / max(len(text), 1)
    if garbage_ratio > 0.1:
        return False

    return True


# ─────────────────────────────────────────────
# MAIN LOADER
# ─────────────────────────────────────────────

def load_patient_pdfs(folder_path: str) -> dict[str, str]:
    """
    Load all PDFs from a patient folder.
    Returns {filename: extracted_text}
    """
    folder = Path(folder_path)
    results = {}

    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"[INGESTION] No PDFs found in {folder_path}")
        return results

    for pdf_path in pdf_files:
        print(f"[INGESTION] Processing: {pdf_path.name}")
        try:
            text = extract_pdf(str(pdf_path))
            results[pdf_path.name] = text
            print(f"[INGESTION] ✓ Extracted {len(text)} chars from {pdf_path.name}")
        except Exception as e:
            print(f"[INGESTION] ✗ Failed on {pdf_path.name}: {e}")
            results[pdf_path.name] = ""

    return results


# ─────────────────────────────────────────────
# HYBRID EXTRACTION PIPELINE
# ─────────────────────────────────────────────

def extract_pdf(pdf_path: str) -> str:
    """
    Per-page hybrid extraction:
      1. PyMuPDF  — fast, works if digital text layer exists
      2. Tesseract OCR — for printed scanned pages
      3. Claude Vision — fallback for handwritten / messy pages
    """
    doc = fitz.open(pdf_path)
    full_text = []

    for page_num, page in enumerate(doc):
        digital_text = page.get_text().strip()

        if is_meaningful_text(digital_text):
            # Digital text layer is clean — use directly
            full_text.append(f"[PAGE {page_num + 1} - DIGITAL]\n{digital_text}")

        else:
            # Scanned page — try Tesseract OCR first
            print(f"[INGESTION] Page {page_num + 1} → trying OCR")
            ocr_text = run_ocr(pdf_path, page_num)

            if is_meaningful_text(ocr_text):
                full_text.append(f"[PAGE {page_num + 1} - OCR]\n{ocr_text}")

            else:
                # OCR not confident enough — Claude Vision fallback
                print(f"[INGESTION] Page {page_num + 1} → Vision fallback")
                vision_text = run_vision(pdf_path, page_num)
                full_text.append(f"[PAGE {page_num + 1} - VISION]\n{vision_text}")

    doc.close()
    return "\n\n".join(full_text)
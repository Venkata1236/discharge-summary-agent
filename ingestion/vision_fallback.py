import os
import base64
import anthropic
from pdf2image import convert_from_path
from io import BytesIO
from PIL import Image


# ─────────────────────────────────────────────
# CLAUDE VISION FALLBACK
# ─────────────────────────────────────────────

def run_vision(pdf_path: str, page_num: int) -> str:
    """
    Send a scanned PDF page to Claude Vision for extraction.
    Used when PyMuPDF and Tesseract both fail to extract meaningful text.
    Best for: handwritten nursing notes, drug charts, mixed Kannada/English pages.
    """
    try:
        # Convert target page to image
        images = convert_from_path(
            pdf_path,
            first_page=page_num + 1,
            last_page=page_num + 1,
            dpi=200          # 200 DPI is enough for Vision — saves tokens
        )

        if not images:
            print(f"[VISION] No image generated for page {page_num + 1}")
            return ""

        img = images[0]

        # Convert to JPEG bytes → base64
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        img_b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")

        # Send to Claude Vision
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": img_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": (
                                "This is a scanned clinical hospital document. "
                                "Extract ALL text exactly as it appears on the page. "
                                "Include every medical term, lab value, date, medication name, "
                                "dosage, vital sign, and handwritten note you can read. "
                                "If text is partially illegible, include your best read followed by [ILLEGIBLE]. "
                                "Do NOT summarize. Do NOT interpret. Transcribe everything."
                            )
                        }
                    ]
                }
            ]
        )

        extracted = response.content[0].text.strip()
        print(f"[VISION] ✓ Page {page_num + 1} — {len(extracted)} chars extracted")
        return extracted

    except Exception as e:
        print(f"[VISION] ✗ Failed on page {page_num + 1}: {e}")
        return ""
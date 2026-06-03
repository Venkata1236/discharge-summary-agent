import os
import pytesseract
from pdf2image import convert_from_path
from PIL import ImageEnhance, ImageFilter, Image


# ─────────────────────────────────────────────
# TESSERACT PATH — set from .env
# ─────────────────────────────────────────────

tesseract_path = os.getenv("TESSERACT_PATH")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path


# ─────────────────────────────────────────────
# IMAGE PREPROCESSING
# ─────────────────────────────────────────────

def preprocess_image(img: Image.Image) -> Image.Image:
    """
    Enhance scanned image before OCR.
    Improves accuracy on low-quality clinical scans.
    """
    # Convert to grayscale
    img = img.convert("L")

    # Boost contrast — helps with faded stamps and light ink
    img = ImageEnhance.Contrast(img).enhance(2.0)

    # Sharpen edges — helps with blurry scans
    img = img.filter(ImageFilter.SHARPEN)

    # Denoise slightly
    img = img.filter(ImageFilter.MedianFilter(size=3))

    return img


# ─────────────────────────────────────────────
# OCR ENGINE
# ─────────────────────────────────────────────

def run_ocr(pdf_path: str, page_num: int) -> str:
    """
    Convert a single PDF page to image and run Tesseract OCR.
    Returns extracted text or empty string on failure.
    """
    try:
        # Convert only the target page — avoids loading full PDF
        images = convert_from_path(
            pdf_path,
            first_page=page_num + 1,
            last_page=page_num + 1,
            dpi=300          # 300 DPI is the sweet spot for clinical docs
        )

        if not images:
            print(f"[OCR] No image generated for page {page_num + 1}")
            return ""

        img = preprocess_image(images[0])

        # Run Tesseract with clinical config
        # psm 6 = assume uniform block of text (works well for forms)
        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, lang="eng", config=custom_config)

        print(f"[OCR] ✓ Page {page_num + 1} — {len(text.strip())} chars extracted")
        text = text.replace("\x0c", "").strip()
        return text

    except Exception as e:
        print(f"[OCR] ✗ Failed on page {page_num + 1}: {e}")
        return ""
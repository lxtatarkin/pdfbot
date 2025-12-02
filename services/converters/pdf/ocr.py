from pathlib import Path
from io import BytesIO

import fitz
import pytesseract
from PIL import Image

from settings import FILES_DIR, logger


def ocr_pdf_to_txt(pdf_path: Path, user_id: int, lang: str = "rus+eng") -> Path | None:
    """
    OCR для PDF: создаёт TXT-файл с распознанным текстом.
    Возвращает путь к TXT или None при ошибке/пустом тексте.
    """
    try:
        pdf_doc = fitz.open(str(pdf_path))
    except Exception as e:
        logger.error(f"OCR PDF open error: {e}")
        return None

    all_text_parts: list[str] = []

    try:
        for page_index, page in enumerate(pdf_doc, start=1):
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            img = Image.open(BytesIO(img_bytes))

            text_page = pytesseract.image_to_string(
                img,
                lang=lang,
            )
            all_text_parts.append(text_page)
    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        return None

    full_text = "\n\n".join(all_text_parts).strip()
    if not full_text:
        return None

    txt_path = FILES_DIR / (pdf_path.stem + "_ocr.txt")
    txt_path.write_text(full_text, encoding="utf-8")
    return txt_path
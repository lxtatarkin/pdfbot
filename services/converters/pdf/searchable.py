from pathlib import Path
from io import BytesIO

import fitz
import pytesseract
from PIL import Image
from PyPDF2 import PdfMerger, PdfReader

from settings import FILES_DIR, logger


def create_searchable_pdf(pdf_path: Path, lang: str = "rus+eng") -> Path | None:
    """
    Создаёт searchable PDF из сканированного PDF.
    Возвращает путь к новому PDF или None при ошибке.
    """
    try:
        pdf_doc = fitz.open(str(pdf_path))
    except Exception as e:
        logger.error(f"Searchable PDF open error: {e}")
        return None

    merger = PdfMerger()
    try:
        for page_index, page in enumerate(pdf_doc, start=1):
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            img = Image.open(BytesIO(img_bytes))

            pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                img,
                extension="pdf",
                lang=lang,
            )

            merger.append(PdfReader(BytesIO(pdf_bytes)))

        out_path = FILES_DIR / f"{pdf_path.stem}_searchable.pdf"
        with open(out_path, "wb") as f:
            merger.write(f)
        merger.close()
        pdf_doc.close()
    except Exception as e:
        logger.error(f"Searchable PDF error: {e}")
        return None

    return out_path if out_path.exists() else None
from pathlib import Path

from PyPDF2 import PdfReader

from settings import logger


def extract_text_from_pdf(pdf_path: Path) -> str | None:
    """
    Извлекает текст из обычного PDF (не скана).
    Возвращает строку или None при ошибке/отсутствии текста.
    """
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        logger.error(f"PDF text open error: {e}")
        return None

    text_chunks: list[str] = []
    try:
        for page in reader.pages:
            txt = page.extract_text() or ""
            text_chunks.append(txt)
    except Exception as e:
        logger.error(f"PDF text extract error: {e}")
        return None

    text_full = "\n\n".join(text_chunks).strip()
    return text_full or None
from pathlib import Path
from typing import Sequence

from PyPDF2 import PdfMerger

from settings import logger


def merge_pdfs(pdf_paths: Sequence[Path], out_path: Path) -> Path | None:
    """
    Объединяет несколько PDF в один.
    out_path — полный путь к итоговому файлу.
    Возвращает out_path или None при ошибке.
    """
    if not pdf_paths:
        return None

    try:
        merger = PdfMerger()
        for p in pdf_paths:
            merger.append(str(p))
        with open(out_path, "wb") as f:
            merger.write(f)
        merger.close()
    except Exception as e:
        logger.error(f"Merge PDFs error: {e}")
        return None

    return out_path if out_path.exists() else None
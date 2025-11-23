from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from settings import FILES_DIR, logger


def split_pdf_to_pages(pdf_path: Path):
    """
    Разбивает PDF на отдельные страницы.
    Возвращает список путей к новым PDF.
    """
    out_files = []

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        logger.error(f"Split open error: {e}")
        return None

    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)

        out_path = FILES_DIR / f"{pdf_path.stem}_page_{i}.pdf"
        try:
            with open(out_path, "wb") as f:
                writer.write(f)
            out_files.append(out_path)
        except Exception as e:
            logger.error(f"Split write error: {e}")
            return None

    return out_files

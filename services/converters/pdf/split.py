from pathlib import Path

from PyPDF2 import PdfReader, PdfWriter

from settings import FILES_DIR, logger


def split_pdf_to_pages(pdf_path: Path) -> list[Path] | None:
    """
    Делит PDF на отдельные страницы.
    Возвращает:
      - None — если не удалось открыть файл,
      - []   — если в документе 1 страница,
      - список путей к созданным PDF-страницам.
    """
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        logger.error(f"Split PDF open error: {e}")
        return None

    n = len(reader.pages)
    if n <= 1:
        return []

    pages_paths: list[Path] = []
    base = pdf_path.stem

    try:
        for i in range(n):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            out_path = FILES_DIR / f"{base}_page_{i + 1}.pdf"
            with open(out_path, "wb") as f:
                writer.write(f)
            pages_paths.append(out_path)
    except Exception as e:
        logger.error(f"Split PDF write error: {e}")
        return None

    return pages_paths

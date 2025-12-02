from pathlib import Path

from PIL import Image

from settings import FILES_DIR, logger


def image_file_to_pdf(src_path: Path) -> Path | None:
    """
    Конвертирует файл-изображение в PDF.
    Возвращает путь к PDF или None при ошибке.
    """
    pdf_path = FILES_DIR / (src_path.stem + ".pdf")
    try:
        img = Image.open(src_path).convert("RGB")
        img.save(pdf_path, "PDF")
    except Exception as e:
        logger.error(f"Image to PDF error: {e}")
        return None

    return pdf_path if pdf_path.exists() else None

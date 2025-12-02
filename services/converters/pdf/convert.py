from pathlib import Path
from typing import Optional

from services.converters.image_to_pdf import image_file_to_pdf
from services.converters.office_to_pdf import office_doc_to_pdf


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
OFFICE_EXTS = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp"}


def convert_to_pdf(src_path: Path) -> Optional[Path]:
    """
    Универсальная конвертация любого поддерживаемого файла в PDF.
    Если файл уже PDF — возвращает его как есть.
    """
    suffix = src_path.suffix.lower()

    if suffix == ".pdf":
        return src_path

    if suffix in IMAGE_EXTS:
        return image_file_to_pdf(src_path)

    if suffix in OFFICE_EXTS:
        return office_doc_to_pdf(src_path)

    return None
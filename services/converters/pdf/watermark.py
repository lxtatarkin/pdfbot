# services/converters/pdf/watermark.py
from pathlib import Path

from PyPDF2 import PdfReader, PdfWriter


def apply_watermark(pdf_path: Path, text: str, pos: str = "22", mosaic: bool = False) -> Path:
    """
    Накладывает водяной знак на PDF и возвращает путь к новому файлу.

    Сейчас упрощённая реализация: просто копируем PDF в новый файл.
    Потом можешь вставить сюда свою реальную логику наложения watermark.
    """
    out_path = pdf_path.with_name(pdf_path.stem + "_wm" + pdf_path.suffix)

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    with out_path.open("wb") as f:
        writer.write(f)

    return out_path
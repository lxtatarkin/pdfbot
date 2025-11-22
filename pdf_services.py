# pdf_services.py
from pathlib import Path

import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from settings import FILES_DIR, logger
from io import BytesIO
from typing import Sequence

import pytesseract
from PIL import Image
from PyPDF2 import PdfMerger


def apply_watermark(pdf_in: Path, wm_text: str, pos: str, mosaic: bool) -> Path | None:
    """
    Нанесение водяного знака на PDF.
    pos — "rc" (r,c = 0..2) позиция в сетке 3×3, если mosaic = False.
    Если mosaic = True — делаем простую "мозаику" текста по всей странице.
    """
    pdf_out = FILES_DIR / f"{pdf_in.stem}_watermark.pdf"

    try:
        doc = fitz.open(str(pdf_in))
    except Exception as e:
        logger.error(f"Watermark open error: {e}")
        return None

    try:
        for page in doc:
            rect = page.rect
            w, h = rect.width, rect.height

            fontsize = max(w, h) / 25
            color = (0.7, 0.7, 0.7)

            if mosaic:
                # простая "мозаика": сетка 4×4 по всей странице
                rows = 4
                cols = 4
                step_x = w / cols
                step_y = h / rows
                for i in range(rows):
                    for j in range(cols):
                        x = (j + 0.5) * step_x
                        y = (i + 0.5) * step_y
                        point = fitz.Point(x, y)
                        page.insert_text(
                            point,
                            wm_text,
                            fontsize=fontsize * 0.7,
                            color=color,
                        )
            else:
                # одиночный watermark по сетке 3×3
                try:
                    row = int(pos[0])
                    col = int(pos[1])
                except Exception:
                    row, col = 1, 1  # по центру по умолчанию

                xs = [w * 0.17, w * 0.5, w * 0.83]
                ys = [h * 0.2, h * 0.5, h * 0.8]

                x = xs[min(max(col, 0), 2)]
                y = ys[min(max(row, 0), 2)]

                point = fitz.Point(x, y)

                page.insert_text(
                    point,
                    wm_text,
                    fontsize=fontsize,
                    color=color,
                )

        doc.save(str(pdf_out))
        doc.close()
    except Exception as e:
        logger.error(f"Watermark apply error: {e}")
        return None

    return pdf_out


def parse_page_range(range_str: str, max_pages: int) -> list[int]:
    """
    '1-3,5,7-9' → [1,2,3,5,7,8,9]
    Страницы считаются с 1. Всё, что выходит за пределы, отбрасывается.
    """
    pages: set[int] = set()
    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_s, end_s = part.split("-", 1)
                start = int(start_s)
                end = int(end_s)
            except ValueError:
                continue
            if start > end:
                start, end = end, start
            for p in range(start, end + 1):
                if 1 <= p <= max_pages:
                    pages.add(p)
        else:
            try:
                p = int(part)
            except ValueError:
                continue
            if 1 <= p <= max_pages:
                pages.add(p)
    return sorted(pages)


def rotate_page_inplace(page, angle: int):
    """
    Поворачивает страницу PyPDF2 на указанный угол (кратный 90).
    Работает и с PyPDF2 >= 3.0.0 (page.rotate), и со старыми версиями.
    """
    from settings import logger as _logger  # чтобы не было циклического импорта (на всякий случай)

    angle = angle % 360
    if angle == 0:
        return

    rotate_method = getattr(page, "rotate", None)
    if callable(rotate_method):
        rotate_method(angle)
        return

    try:
        if angle == 90:
            page.rotateClockwise(90)
        elif angle == 180:
            page.rotateClockwise(180)
        elif angle == 270:
            page.rotateCounterClockwise(90)
    except Exception as e:
        _logger.error(f"Page rotate fallback error: {e}")


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
            img_path = FILES_DIR / f"ocr_{user_id}_{page_index}.png"
            pix.save(img_path)

            text_page = pytesseract.image_to_string(
                str(img_path),
                lang=lang
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
                lang=lang
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
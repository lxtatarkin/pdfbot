# pdf_services.py
from pathlib import Path

import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from settings import FILES_DIR, logger


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
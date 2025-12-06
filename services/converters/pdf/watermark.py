# services/converters/pdf/watermark.py
from pathlib import Path
from io import BytesIO
from typing import Tuple

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def _parse_pos(pos: str) -> Tuple[int, int]:
    """
    Преобразует код позиции '11'..'33' в (row, col) от 1 до 3.
    1 — верх/лево, 3 — низ/право.
    """
    try:
        if len(pos) == 2 and pos.isdigit():
            row = int(pos[0])
            col = int(pos[1])
        else:
            row, col = 2, 2
    except Exception:
        row, col = 2, 2

    row = min(max(row, 1), 3)
    col = min(max(col, 1), 3)
    return row, col


def _pos_to_coords(pos: str, width: float, height: float) -> Tuple[float, float]:
    """
    Возвращает координаты (x, y) для текста по сетке 3×3
    с учётом полей.

    Используем поля ~15% по краям, и равномерно делим
    внутреннюю область на 3×3.
    """
    row, col = _parse_pos(pos)

    # Поля с каждой стороны (15% от размера страницы)
    margin_x = width * 0.15
    margin_y = height * 0.15

    inner_width = width - 2 * margin_x
    inner_height = height - 2 * margin_y

    # col: 1..3 слева направо
    # row: 1..3 сверху вниз
    # горизонталь
    x = margin_x + (col - 1) * (inner_width / 2.0)
    # вертикаль: row=1 — верх, а система координат снизу,
    # поэтому считаем "сверху вниз"
    y = height - margin_y - (row - 1) * (inner_height / 2.0)

    return x, y


def _make_watermark_page(
    text: str,
    width: float,
    height: float,
    pos: str = "22",
    mosaic: bool = False,
) -> BytesIO:
    """
    Создаёт одну PDF-страницу с водяным знаком в памяти и
    возвращает BytesIO с готовым PDF.
    """
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(width, height))

    # базовый размер шрифта от размера страницы
    base_font_size = max(12, min(width, height) * 0.04)
    c.setFont("Helvetica", base_font_size)
    c.setFillGray(0.6)  # серый текст

    if mosaic:
        # Тиражируем текст по всей странице
        step_x = base_font_size * 6
        step_y = base_font_size * 4

        for xx in range(0, int(width) + int(step_x), int(step_x)):
            for yy in range(0, int(height) + int(step_y), int(step_y)):
                c.saveState()
                c.translate(xx, yy)
                c.rotate(30)
                c.drawString(0, 0, text)
                c.restoreState()
    else:
        # Одна надпись в нужной позиции
        x, y = _pos_to_coords(pos, width, height)
        c.saveState()
        c.translate(x, y)
        c.rotate(30)
        # Центруем по точке (0,0) – она стоит в центре области,
        # так что текст визуально будет «по центру» выбранной ячейки.
        c.drawCentredString(0, 0, text)
        c.restoreState()

    c.showPage()
    c.save()
    packet.seek(0)
    return packet


def apply_watermark(
    pdf_path: Path,
    text: str,
    pos: str = "22",
    mosaic: bool = False,
) -> Path:
    """
    Накладывает текстовый водяной знак на все страницы PDF и
    возвращает путь к новому файлу.

    pos — позиция по сетке 3×3:
        '11' — верхний левый угол,
        '12' — верх по центру,
        '13' — верхний правый,
        '21'/'22'/'23' — центр,
        '31'/'32'/'33' — низ.

    mosaic=True — заполняет всю страницу повторяющимся текстом.
    """
    out_path = pdf_path.with_name(pdf_path.stem + "_wm" + pdf_path.suffix)

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    for page in reader.pages:
        # размеры страницы
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        # генерируем watermark-страницу в памяти
        wm_buffer = _make_watermark_page(
            text=text,
            width=width,
            height=height,
            pos=pos,
            mosaic=mosaic,
        )
        wm_reader = PdfReader(wm_buffer)
        wm_page = wm_reader.pages[0]

        # накладываем watermark на текущую страницу
        page.merge_page(wm_page)
        writer.add_page(page)

    with out_path.open("wb") as f:
        writer.write(f)

    return out_path
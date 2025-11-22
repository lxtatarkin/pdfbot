# keyboards.py
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📉 Сжать PDF"),
                KeyboardButton(text="📎 Объединить PDF"),
            ],
            [
                KeyboardButton(text="✂️ Разделить PDF"),
                KeyboardButton(text="📝 PDF → текст"),
            ],
            [
                KeyboardButton(text="📄 Документ/фото → PDF"),
            ],
            [
                KeyboardButton(text="🔍 OCR"),
                KeyboardButton(text="📑 Searchable PDF"),
            ],
            [
                KeyboardButton(text="🧩 Редактор страниц"),
                KeyboardButton(text="🛡 Водяной знак"),
            ],
        ],
        resize_keyboard=True
    )


def get_pages_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Основное меню редактора страниц.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Поворот страниц",
                    callback_data="pages_action:rotate"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить страницы",
                    callback_data="pages_action:delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📤 Извлечь страницы",
                    callback_data="pages_action:extract"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="pages_action:cancel"
                )
            ],
        ]
    )


def get_rotate_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора угла поворота.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="+90°", callback_data="pages_rotate_angle:+90"),
                InlineKeyboardButton(text="-90°", callback_data="pages_rotate_angle:-90"),
                InlineKeyboardButton(text="180°", callback_data="pages_rotate_angle:180"),
            ],
            [
                InlineKeyboardButton(text="↩️ Назад к меню", callback_data="pages_back_to_menu")
            ]
        ]
    )


def get_watermark_keyboard(pos: str | None = None, mosaic: bool = False) -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура 3×3 для выбора позиции + чекбокс Mosaic + кнопка OK.
    pos — строка вида "rc" (row, col), где r,c в [0..2].
    """
    grid: list[list[InlineKeyboardButton]] = []

    for r in range(3):
        row: list[InlineKeyboardButton] = []
        for c in range(3):
            code = f"{r}{c}"
            text = "●" if pos == code else " "
            row.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"wm_pos:{code}"
                )
            )
        grid.append(row)

    mosaic_text = "✅ Mosaic" if mosaic else "Mosaic"
    grid.append([
        InlineKeyboardButton(text=mosaic_text, callback_data="wm_toggle_mosaic")
    ])
    grid.append([
        InlineKeyboardButton(text="OK", callback_data="wm_apply")
    ])

    return InlineKeyboardMarkup(inline_keyboard=grid)

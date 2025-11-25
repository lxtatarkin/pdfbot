# keyboards.py
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from i18n import t


def get_main_keyboard(user_id: int = 0) -> ReplyKeyboardMarkup:
    """
    Основная клавиатура.
    Если user_id == 0, используем язык по умолчанию (en).
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t(user_id, "btn_main_compress")),
                KeyboardButton(text=t(user_id, "btn_main_merge")),
            ],
            [
                KeyboardButton(text=t(user_id, "btn_main_split")),
                KeyboardButton(text=t(user_id, "btn_main_pdf_to_text")),
            ],
            [
                KeyboardButton(text=t(user_id, "btn_main_doc_to_pdf")),
            ],
            [
                KeyboardButton(text=t(user_id, "btn_main_ocr")),
                KeyboardButton(text=t(user_id, "btn_main_searchable")),
            ],
            [
                KeyboardButton(text=t(user_id, "btn_main_pages")),
                KeyboardButton(text=t(user_id, "btn_main_watermark")),
            ],
        ],
        resize_keyboard=True,
    )


def get_pages_menu_keyboard(user_id: int = 0) -> InlineKeyboardMarkup:
    """
    Основное меню редактора страниц.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(user_id, "pages_rotate"),
                    callback_data="pages_action:rotate",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pages_delete"),
                    callback_data="pages_action:delete",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pages_extract"),
                    callback_data="pages_action:extract",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pages_cancel"),
                    callback_data="pages_action:cancel",
                )
            ],
        ]
    )


def get_rotate_keyboard(user_id: int = 0) -> InlineKeyboardMarkup:
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
                InlineKeyboardButton(
                    text=t(user_id, "pages_back"),
                    callback_data="pages_back_to_menu",
                )
            ],
        ]
    )


def get_watermark_keyboard(
    user_id: int = 0,
    pos: str | None = None,
    mosaic: bool = False,
) -> InlineKeyboardMarkup:
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
                    callback_data=f"wm_pos:{code}",
                )
            )
        grid.append(row)

    mosaic_text = f"✅ {t(user_id, 'wm_mosaic')}" if mosaic else t(user_id, "wm_mosaic")
    grid.append(
        [
            InlineKeyboardButton(
                text=mosaic_text,
                callback_data="wm_toggle_mosaic",
            )
        ]
    )
    grid.append(
        [
            InlineKeyboardButton(
                text=t(user_id, "wm_ok"),
                callback_data="wm_apply",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=grid)

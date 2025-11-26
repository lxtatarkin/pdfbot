import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from i18n import t, set_user_lang
from state import is_pro_user

router = Router()

APP_BASE_URL = os.getenv("APP_BASE_URL", "").rstrip("/")

# ID цен из Stripe (для читаемости отдельные переменные)
PRICE_MONTH = os.getenv("STRIPE_PRICE_ID_MONTH")
PRICE_QUARTER = os.getenv("STRIPE_PRICE_ID_QUARTER")
PRICE_YEAR = os.getenv("STRIPE_PRICE_ID_YEAR")


@router.message(Command("pro"))
async def cmd_pro(message: Message):
    user = message.from_user
    if not user:
        return

    user_id = user.id

    # фиксируем язык пользователя в i18n
    set_user_lang(user_id, user.language_code)

    # уже PRO
    if is_pro_user(user_id):
        await message.answer(
            t(user_id, "pro_already", max_size="100 MB"),
            parse_mode="HTML",
        )
        return

    # если APP_BASE_URL или цены не заданы — показываем старый текст без кнопок
    if not APP_BASE_URL or not (PRICE_MONTH and PRICE_QUARTER and PRICE_YEAR):
        await message.answer(
            t(user_id, "pro_info"),
            parse_mode="HTML",
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_month"),
                    url=f"{APP_BASE_URL}/buy-pro?user_id={user_id}&price_id={PRICE_MONTH}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_quarter"),
                    url=f"{APP_BASE_URL}/buy-pro?user_id={user_id}&price_id={PRICE_QUARTER}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_year"),
                    url=f"{APP_BASE_URL}/buy-pro?user_id={user_id}&price_id={PRICE_YEAR}",
                )
            ],
        ]
    )

    await message.answer(
        t(user_id, "pro_info_short"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )

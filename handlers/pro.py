import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from i18n import t
from state import is_pro_user

router = Router()

APP_BASE_URL = os.getenv("APP_BASE_URL", "").rstrip("/")  # чтобы не было двойного //


@router.message(Command("pro"))
async def cmd_pro(message: Message):
    user_id = message.from_user.id

    # пользователь уже PRO
    if is_pro_user(user_id):
        await message.answer(
            t(user_id, "pro_already", max_size="100 MB"),
            parse_mode="HTML",
        )
        return

    if not APP_BASE_URL:
        # на всякий случай – если переменная не задана, показываем старый текст без кнопки
        await message.answer(
            t(user_id, "pro_info"),
            parse_mode="HTML",
        )
        return

    pay_url = f"{APP_BASE_URL}/buy-pro?user_id={user_id}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Купить PRO",
                    url=pay_url,
                )
            ]
        ]
    )

    await message.answer(
        t(user_id, "pro_info_short"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )

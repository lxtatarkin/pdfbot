from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from i18n import t
from state import is_pro_user
import os

router = Router()

APP_BASE_URL = os.getenv("APP_BASE_URL")


@router.message(F.text == "/pro")
async def cmd_pro(message: Message):
    user_id = message.from_user.id

    # пользователь уже PRO
    if is_pro_user(user_id):
        await message.answer(
            t(user_id, "pro_already", max_size="100 MB"),
            parse_mode="HTML"
        )
        return

    # кнопка оплатить
    pay_url = f"{APP_BASE_URL}/buy-pro?user_id={user_id}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Купить PRO", url=pay_url
                )
            ]
        ]
    )

    await message.answer(
        t(user_id, "pro_info_short"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )

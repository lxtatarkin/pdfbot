import os

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from i18n import t, get_user_lang
from state import is_pro_user  # эта функция должна дергать /is-pro на billing

router = Router()

# Базовый URL биллинга (pdfbot-billing)
BILLING_BASE_URL = os.getenv("APP_BASE_URL")  # в pdfbot-staging он у тебя уже такой


@router.message(F.text == "/pro")
async def cmd_pro(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    # Уже PRO → текст + кнопка "Управлять подпиской"
    if is_pro_user(user_id):
        manage_url = (
            f"{BILLING_BASE_URL}/customer-portal?user_id={user_id}&lang={lang}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(user_id, "pro_manage_btn"),
                        url=manage_url,
                    )
                ]
            ]
        )

        await message.answer(
            t(user_id, "pro_already", max_size="100 MB"),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return

    # Нет PRO → показываем планы
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_month"),
                    url=(
                        f"{BILLING_BASE_URL}/buy-pro"
                        f"?user_id={user_id}&plan=month&lang={lang}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_quarter"),
                    url=(
                        f"{BILLING_BASE_URL}/buy-pro"
                        f"?user_id={user_id}&plan=quarter&lang={lang}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_year"),
                    url=(
                        f"{BILLING_BASE_URL}/buy-pro"
                        f"?user_id={user_id}&plan=year&lang={lang}"
                    ),
                )
            ],
        ]
    )

    await message.answer(
        t(user_id, "pro_info_short"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
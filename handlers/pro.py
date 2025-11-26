import os

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from i18n import t, get_user_lang
from state import is_pro_user

router = Router()

APP_BASE_URL = os.getenv("APP_BASE_URL")  # тот же, что у billing


@router.message(F.text == "/pro")
async def cmd_pro(message: Message):
    user_id = message.from_user.id

    # Язык пользователя (ru/en) из i18n-хранилища
    lang = get_user_lang(user_id)

    # Если уже PRO — показываем статусы + кнопку управления подпиской
    if is_pro_user(user_id):
        manage_url = f"{APP_BASE_URL}/customer-portal?user_id={user_id}&lang={lang}"

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

    # Иначе — экран покупки PRO (оставь как было, либо вот так)
    pay_url = f"{APP_BASE_URL}/buy-pro?user_id={user_id}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_month"),
                    url=f"{APP_BASE_URL}/buy-pro?user_id={user_id}&price_id=price_month_placeholder",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_quarter"),
                    url=f"{APP_BASE_URL}/buy-pro?user_id={user_id}&price_id=price_quarter_placeholder",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_year"),
                    url=f"{APP_BASE_URL}/buy-pro?user_id={user_id}&price_id=price_year_placeholder",
                )
            ],
        ]
    )
    # или используй твой текущий вариант с одной кнопкой, если он уже работает

    await message.answer(
        t(user_id, "pro_info_short"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
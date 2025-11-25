import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from i18n import set_user_lang, t  # используем твою i18n

router = Router()

PAYMENTS_URL = os.getenv("PAYMENTS_URL", "").rstrip("/")

# Временная логика PRO: читаем из ENV, как раньше
PRO_USERS_RAW = os.getenv("PRO_USERS", "")
PRO_USERS: set[int] = set()
for part in PRO_USERS_RAW.split(","):
    part = part.strip()
    if part.isdigit():
        PRO_USERS.add(int(part))


def is_pro(user_id: int) -> bool:
    return user_id in PRO_USERS


@router.message(Command("pro"))
async def pro_command(message: Message):
    user = message.from_user
    if not user:
        return

    user_id = user.id

    # Фиксируем язык пользователя так же, как везде
    lang = set_user_lang(user_id, user.language_code)

    # Если уже PRO — просто показываем инфу
    if is_pro(user_id):
        text = t(user_id, "pro_already", max_size="100 MB")
        await message.answer(text)
        return

    # Проверяем, настроен ли payments-сервис
    if not PAYMENTS_URL:
        # fallback, пока нет Stripe / переменной
        await message.answer(t(user_id, "pro_info"))
        return

    info_text = t(user_id, "pro_info")
    pay_hint = t(user_id, "pro_pay_hint")
    full_text = info_text + "\n\n" + pay_hint

    pay_url = f"{PAYMENTS_URL}/buy-pro?user_id={user_id}&lang={lang}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_pay_button"),
                    url=pay_url,
                )
            ]
        ]
    )

    await message.answer(full_text, reply_markup=keyboard)

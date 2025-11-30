# handlers/support.py
import os
from datetime import datetime

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from i18n import t, get_user_lang

router = Router()

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0")
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    ADMIN_ID = 0  # если криво настроен, не валим бота


@router.message(Command("support"))
async def support_cmd(message: Message, bot: Bot):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    if ADMIN_ID == 0:
        # админ не настроен
        await message.answer(
            "Support is not configured yet. Try again later."
            if lang != "ru"
            else "Поддержка пока не настроена. Попробуйте позже.",
        )
        return

    # ожидаем формат: /support текст проблемы
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            t(user_id, "support_usage"),
            parse_mode="HTML",
        )
        return

    user_text = parts[1]

    username = message.from_user.username
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""

    lines = [
        "🆘 Новое сообщение в поддержку",
        "",
        f"ID: {user_id}",
        f"Username: @{username}" if username else "Username: (нет)",
        f"Имя: {first_name} {last_name}".strip(),
        f"Язык: {lang}",
        "",
        "Текст:",
        user_text,
        "",
        f"Время: {datetime.utcnow().isoformat()}Z",
    ]
    admin_text = "\n".join(lines)

    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_text)
    except Exception:
        await message.answer(
            t(user_id, "support_error"),
            parse_mode="HTML",
        )
        return

    await message.answer(
        t(user_id, "support_sent"),
        parse_mode="HTML",
    )
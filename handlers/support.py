# handlers/support.py
import os
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message

from i18n import t, get_user_lang

router = Router()

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Примитивное состояние "жду текст для поддержки"
WAITING_SUPPORT = set[int]()


@router.message(Command("support"))
async def support_cmd(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    if ADMIN_ID == 0:
        # если админ не настроен — скажем пользователю честно
        await message.answer(
            "Support is not configured yet. Try again later."
            if lang != "ru"
            else "Поддержка пока не настроена. Попробуйте позже.",
        )
        return

    WAITING_SUPPORT.add(user_id)

    await message.answer(
        t(user_id, "support_intro"),
        parse_mode="HTML",
    )


@router.message(Command("support_cancel"))
async def support_cancel_cmd(message: Message):
    user_id = message.from_user.id

    if user_id in WAITING_SUPPORT:
        WAITING_SUPPORT.discard(user_id)
        await message.answer(
            t(user_id, "support_cancelled"),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            t(user_id, "support_not_waiting"),
            parse_mode="HTML",
        )


@router.message(F.text)
async def support_text_handler(message: Message, bot: Bot):
    user_id = message.from_user.id

    # Если не ждём сообщение для поддержки — пропускаем, пусть обрабатывают другие роутеры
    if user_id not in WAITING_SUPPORT:
        return

    # Выходим из режима поддержки
    WAITING_SUPPORT.discard(user_id)

    if ADMIN_ID == 0:
        await message.answer(
            "Support is not configured yet."
            if get_user_lang(user_id) != "ru"
            else "Поддержка пока не настроена.",
        )
        return

    # Текст пользователя
    user_text = message.text or ""
    lang = get_user_lang(user_id)

    # Формируем сообщение админу
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    lines = [
        f"🆘 Новое сообщение в поддержку",
        "",
        f"ID: {user_id}",
        f"Username: @{username}" if username else "Username: (нет)",
        f"Имя: {first_name or ''} {last_name or ''}".strip(),
        f"Язык: {lang}",
        "",
        "Текст:",
        user_text,
        "",
        f"Время: {datetime.utcnow().isoformat()}Z",
    ]

    admin_text = "\n".join(lines)

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
        )
    except Exception:
        # если что-то пошло не так
        await message.answer(
            t(user_id, "support_error"),
            parse_mode="HTML",
        )
        return

    await message.answer(
        t(user_id, "support_sent"),
        parse_mode="HTML",
    )
# handlers/start.py
import os

from aiogram import Router, types, Bot
from aiogram.filters import Command

from settings import (
    is_pro,
    get_user_limit,
    format_mb,
    logger,
    PRO_MAX_SIZE,
    FREE_MAX_SIZE,
)
from state import (
    user_modes,
    user_merge_files,
    user_watermark_state,
    user_pages_state,
)
from keyboards import get_main_keyboard
from i18n import set_user_lang, t, get_user_lang
from legal import PRIVACY_URL, TERMS_URL  # нужно для footer_legal

router = Router()

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0")
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    ADMIN_ID = 0


@router.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    tg_lang = message.from_user.language_code

    # автоопределение языка
    lang = set_user_lang(user_id, tg_lang)

    # сброс состояния пользователя
    user_modes[user_id] = "compress"
    user_merge_files[user_id] = []
    user_watermark_state[user_id] = {}
    user_pages_state[user_id] = {}

    # ------- ПРОВЕРКА ПРО-СТАТУСА ----------
    is_pro_now = is_pro(user_id)
    tier = "PRO" if is_pro_now else "FREE"

    # лимит по тарифу
    limit_mb_value = PRO_MAX_SIZE if is_pro_now else FREE_MAX_SIZE
    limit_mb = format_mb(limit_mb_value)

    logger.info(
        f"/start from {user_id} ({username}), tier={tier}, lang={lang}, tg_lang={tg_lang}"
    )

    main_text = t(
        user_id,
        "start_main",
        tier=tier,
        limit_mb=limit_mb,
    )

    footer = t(
        user_id,
        "footer_legal",
        terms=TERMS_URL,
        privacy=PRIVACY_URL,
    )

    await message.answer(
        main_text + "\n\n" + footer,
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML",
    )


@router.message(Command("support"))
async def support_cmd(message: types.Message, bot: Bot):
    """
    Использование: /support <текст сообщения>
    """
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    if ADMIN_ID == 0:
        await message.answer(
            "Support is not configured yet. Try again later."
            if lang != "ru"
            else "Поддержка пока не настроена. Попробуйте позже.",
        )
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        # нет текста после /support
        await message.answer(
            t(user_id, "support_intro"),
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
        "Время: по серверу (UTC).",
    ]
    admin_text = "\n".join(lines)

    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_text)
    except Exception as e:
        logger.error("Failed to send support message to admin: %s", e)
        await message.answer(
            t(user_id, "support_error"),
            parse_mode="HTML",
        )
        return

    await message.answer(
        t(user_id, "support_sent"),
        parse_mode="HTML",
    )
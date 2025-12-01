# handlers/start.py
import os

from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from settings import (
    is_pro,
    get_user_limit,
    format_mb,
    logger,
)
from state import (
    user_modes,
    user_merge_files,
    user_watermark_state,
    user_pages_state,
)
from keyboards import get_main_keyboard
from i18n import set_user_lang, t, get_user_lang
from legal import PRIVACY_URL, TERMS_URL

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

    # сброс состояния пользователя (нормально)
    user_modes[user_id] = "compress"
    user_merge_files[user_id] = []
    user_watermark_state[user_id] = {}
    user_pages_state[user_id] = {}

    # ------- ПРОВЕРКА ПРО-СТАТУСА ЧЕРЕЗ PostgreSQL ----------
    is_pro_now = await is_pro(user_id)
    tier = "PRO" if is_pro_now else "FREE"

    # лимит по тарифу через PostgreSQL
    limit_bytes = await get_user_limit(user_id)
    limit_mb = format_mb(limit_bytes)

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


@router.message(Command("privacy"))
async def privacy_cmd(message: types.Message):
    user_id = message.from_user.id
    # обновим язык по Telegram-коду
    set_user_lang(user_id, message.from_user.language_code)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open",
                    url=PRIVACY_URL,
                )
            ]
        ]
    )

    await message.answer(
        t(user_id, "privacy_link"),
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.message(Command("terms"))
async def terms_cmd(message: types.Message):
    user_id = message.from_user.id
    set_user_lang(user_id, message.from_user.language_code)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open",
                    url=TERMS_URL,
                )
            ]
        ]
    )

    await message.answer(
        t(user_id, "terms_link"),
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.message(Command("support"))
async def support_cmd(message: types.Message, bot: Bot):
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
        "Время будет по серверу, UTC.",
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
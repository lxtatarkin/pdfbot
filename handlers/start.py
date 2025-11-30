# handlers/start.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
from i18n import set_user_lang, t
from legal import PRIVACY_URL, TERMS_URL

router = Router()


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

@router.message(Command("privacy"))
async def privacy_cmd(message: types.Message):
    user_id = message.from_user.id
    # обновим язык по Telegram-коду
    set_user_lang(user_id, message.from_user.language_code)

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            text="Open",
            url=PRIVACY_URL,
        )
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

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            text="Open",
            url=TERMS_URL,
        )
    )

    await message.answer(
        t(user_id, "terms_link"),
        reply_markup=kb,
        parse_mode="HTML",
    )
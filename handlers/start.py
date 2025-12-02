# handlers/start.py
import os

from aiogram import Router, types
from aiogram.filters import Command

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
from i18n import set_user_lang, t
from legal import PRIVACY_URL, TERMS_URL  # можно оставить, если нужны в тексте /start

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

    lang = set_user_lang(user_id, tg_lang)

    user_modes[user_id] = "compress"
    user_merge_files[user_id] = []
    user_watermark_state[user_id] = {}
    user_pages_state[user_id] = {}

    is_pro_now = await is_pro(user_id)
    tier = "PRO" if is_pro_now else "FREE"

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
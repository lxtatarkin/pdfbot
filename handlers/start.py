# handlers/start.py
from aiogram import Router, types
from aiogram.filters import Command

from settings import (
    is_pro,
    get_user_limit,
    format_mb,
    logger,
    PRO_MAX_SIZE,
)
from state import (
    user_modes,
    user_merge_files,
    user_watermark_state,
    user_pages_state,
)
from keyboards import get_main_keyboard
from i18n import set_user_lang, t

router = Router()


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

    tier = "PRO" if is_pro(user_id) else "FREE"
    limit_mb = format_mb(get_user_limit(user_id))

    logger.info(
        f"/start from {user_id} ({username}), tier={tier}, lang={lang}, tg_lang={tg_lang}"
    )
    await message.answer(
        t(user_id, "start_main", tier=tier, limit_mb=limit_mb),
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML",
    )


@router.message(Command("pro"))
async def pro_cmd(message: types.Message):
    user_id = message.from_user.id

    if is_pro(user_id):
        await message.answer(
            t(
                user_id,
                "pro_already",
                max_size=format_mb(PRO_MAX_SIZE),
            ),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            t(user_id, "pro_info"),
            parse_mode="HTML",
        )

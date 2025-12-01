# handlers/legal.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from legal import PRIVACY_URL, TERMS_URL
from i18n import set_user_lang, t

router = Router()


@router.message(Command("privacy"))
async def cmd_privacy(message: types.Message):
    user_id = message.from_user.id
    set_user_lang(user_id, message.from_user.language_code)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open", url=PRIVACY_URL)]
        ]
    )

    await message.answer(
        t(user_id, "privacy_link"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(Command("terms"))
async def cmd_terms(message: types.Message):
    user_id = message.from_user.id
    set_user_lang(user_id, message.from_user.language_code)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open", url=TERMS_URL)]
        ]
    )

    await message.answer(
        t(user_id, "terms_link"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
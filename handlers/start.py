# start.py
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
from i18n import set_user_lang 

router = Router()

@router.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username

    # НОВОЕ: язык телеграма → наш стор
    tg_lang = message.from_user.language_code  # типа 'ru', 'ru-RU', 'en', 'en-US'
    lang = set_user_lang(user_id, tg_lang)

    # сброс состояния пользователя
    user_modes[user_id] = "compress"
    user_merge_files[user_id] = []
    user_watermark_state[user_id] = {}
    user_pages_state[user_id] = {}

    tier = "PRO" if is_pro(user_id) else "FREE"
    limit_mb = format_mb(get_user_limit(user_id))

    logger.info(
        f"/start from {user_id} ({username}), tier={tier}, "
        f"lang={lang}, tg_lang={tg_lang}"
    )

    await message.answer(
        "👋 Привет! Я конвертирую и обрабатываю файлы в PDF.\n\n"
        "Выбери режим на клавиатуре и пришли файл:\n\n"
        "Основные инструменты:\n"
        "• 📉 Сжать PDF\n"
        "• 📎 Объединить PDF\n"
        "• ✂️ Разделить PDF\n"
        "• 📝 PDF → текст\n"
        "• 📄 Документ/фото → PDF\n\n"
        "PRO-инструменты:\n"
        "• 🔍 OCR\n"
        "• 📑 Searchable PDF\n"
        "• 🧩 Редактор страниц\n"
        "• 🛡 Водяной знак\n\n"
        f"Текущий тариф: <b>{tier}</b>\n"
        f"Лимит: <b>{limit_mb}</b>\n\n"
        "Подключить PRO-версию: /pro",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )

@router.message(Command("pro"))
async def pro_cmd(message: types.Message):
    user_id = message.from_user.id
    if is_pro(user_id):
        await message.answer(
            "✅ У вас уже PRO-доступ.\n"
            f"Текущий лимит: {format_mb(PRO_MAX_SIZE)}.\n\n"
            "Доступные PRO-функции:\n"
            "• OCR (сканы/фото → текст)\n"
            "• Searchable PDF (скан → PDF с выделяемым текстом)\n"
            "• Редактор страниц PDF (поворот/удаление/извлечение)\n"
            "• Водяные знаки для PDF\n"
            "• Файлы до 100 МБ",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "💼 <b>PRO-доступ</b>\n\n"
            "Что даёт сейчас:\n"
            "• Лимит до 100 МБ\n"
            "• OCR (сканы и фото → текст)\n"
            "• Searchable PDF (скан → PDF с выделяемым текстом)\n"
            "• Редактор страниц PDF (поворот/удаление/извлечение)\n"
            "• Водяные знаки для PDF\n"
            "• Приоритет в очереди (планируется)\n\n"
            "Чтобы подключить PRO — напишите владельцу бота.",
            parse_mode="HTML",
        )

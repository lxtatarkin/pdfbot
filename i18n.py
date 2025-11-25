from typing import Dict, Optional

# Хранилище выбранных языков пользователей
USER_LANG: Dict[int, str] = {}

# Язык по умолчанию — английский
DEFAULT_LANG = "en"


def detect_lang(language_code: Optional[str]) -> str:
    """
    Определяет язык по коду Telegram.
    Возвращает 'ru' или 'en'.
    """
    if not language_code:
        return DEFAULT_LANG

    code = language_code.lower()

    # Славянские — считаем русским
    if code.startswith("ru") or code.startswith("uk") or code.startswith("be"):
        return "ru"

    # Всё остальное — английский
    return "en"


def set_user_lang(user_id: int, language_code: Optional[str]) -> str:
    """
    Сохраняет язык в словаре USER_LANG.
    """
    lang = detect_lang(language_code)
    USER_LANG[user_id] = lang
    return lang


def get_user_lang(user_id: int) -> str:
    """
    Возвращает язык пользователя, иначе дефолтный.
    """
    return USER_LANG.get(user_id, DEFAULT_LANG)


# ===== ЛОКАЛИЗАЦИЯ ТЕКСТОВ =====

TEXTS: Dict[str, Dict[str, str]] = {
    "ru": {
        "start_main": (
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
            "Текущий тариф: <b>{tier}</b>\n"
            "Лимит: <b>{limit_mb}</b>\n\n"
            "Подключить PRO-версию: /pro"
        ),
        "pro_already": (
            "✅ У вас уже PRO-доступ.\n"
            "Текущий лимит: {max_size}.\n\n"
            "Доступные PRO-функции:\n"
            "• OCR (сканы/фото → текст)\n"
            "• Searchable PDF (скан → PDF с выделяемым текстом)\n"
            "• Редактор страниц PDF (поворот/удаление/извлечение)\n"
            "• Водяные знаки для PDF\n"
            "• Файлы до 100 МБ"
        ),
        "pro_info": (
            "💼 <b>PRO-доступ</b>\n\n"
            "Что даёт сейчас:\n"
            "• Лимит до 100 МБ\n"
            "• OCR (сканы и фото → текст)\n"
            "• Searchable PDF (скан → PDF с выделяемым текстом)\n"
            "• Редактор страниц PDF (поворот/удаление/извлечение)\n"
            "• Водяные знаки для PDF\n"
            "• Приоритет в очереди (планируется)\n\n"
            "Чтобы подключить PRO — напишите владельцу бота."
        ),
    },

    "en": {
        "start_main": (
            "👋 Hi! I convert and process files to PDF.\n\n"
            "Choose a mode on the keyboard and send a file:\n\n"
            "Main tools:\n"
            "• 📉 Compress PDF\n"
            "• 📎 Merge PDF\n"
            "• ✂️ Split PDF\n"
            "• 📝 PDF → text\n"
            "• 📄 Document/Photo → PDF\n\n"
            "PRO tools:\n"
            "• 🔍 OCR\n"
            "• 📑 Searchable PDF\n"
            "• 🧩 Page editor\n"
            "• 🛡 Watermark\n\n"
            "Current plan: <b>{tier}</b>\n"
            "Limit: <b>{limit_mb}</b>\n\n"
            "Upgrade to PRO: /pro"
        ),
        "pro_already": (
            "✅ You already have PRO access.\n"
            "Current limit: {max_size}.\n\n"
            "Available PRO features:\n"
            "• OCR (scans/photos → text)\n"
            "• Searchable PDF (scan → PDF with selectable text)\n"
            "• PDF page editor (rotate/delete/extract)\n"
            "• PDF watermarks\n"
            "• Files up to 100 MB"
        ),
        "pro_info": (
            "💼 <b>PRO access</b>\n\n"
            "What you get now:\n"
            "• Limit up to 100 MB\n"
            "• OCR (scans and photos → text)\n"
            "• Searchable PDF (scan → PDF with selectable text)\n"
            "• PDF page editor (rotate/delete/extract)\n"
            "• PDF watermarks\n"
            "• Priority in queue (planned)\n\n"
            "To get PRO — contact the bot owner."
        ),
    },
}


def _get_text_for_lang(lang: str, key: str) -> str:
    lang_dict = TEXTS.get(lang)
    if not lang_dict:
        lang_dict = TEXTS[DEFAULT_LANG]

    if key in lang_dict:
        return lang_dict[key]

    # если нет ключа — fallback на английский
    default_dict = TEXTS[DEFAULT_LANG]
    return default_dict.get(key, f"[{key}]")  # крайний случай


def t(user_id: int, key: str, **kwargs) -> str:
    lang = get_user_lang(user_id)
    text = _get_text_for_lang(lang, key)

    if kwargs:
        return text.format(**kwargs)

    return text

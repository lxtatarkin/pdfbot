# i18n.py

from typing import Dict, Optional

# Хранилище языков пользователей (в памяти)
USER_LANG: Dict[int, str] = {}

DEFAULT_LANG = "ru"


def detect_lang(language_code: Optional[str]) -> str:
    """
    Определяет язык по коду Telegram.
    Например: 'ru', 'ru-RU', 'en', 'en-US', 'uk', 'be' и т.д.
    """
    if not language_code:
        return DEFAULT_LANG

    code = language_code.lower()

    # Все славянские, близкие к русскому — считаем русским
    if code.startswith("ru") or code.startswith("uk") or code.startswith("be"):
        return "ru"

    # Всё остальное — английский
    return "en"


def set_user_lang(user_id: int, language_code: Optional[str]) -> str:
    """
    Вычисляет язык по language_code и сохраняет для пользователя.
    Возвращает итоговый язык (ru/en).
    """
    lang = detect_lang(language_code)
    USER_LANG[user_id] = lang
    return lang


def get_user_lang(user_id: int) -> str:
    """
    Возвращает язык пользователя, если он уже сохранён,
    иначе дефолтный.
    """
    return USER_LANG.get(user_id, DEFAULT_LANG)
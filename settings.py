# settings.py
import os
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ===== Лимиты =====
FREE_MAX_SIZE = 20 * 1024 * 1024      # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024      # 100 MB

# URL billing-сервиса (pdfbot-billing)
# В pdfbot-staging должна быть переменная окружения:
# BILLING_BASE_URL = https://pdfbot-billing-production.up.railway.app
BILLING_BASE_URL = os.getenv("BILLING_BASE_URL")


def format_mb(size_bytes: int) -> str:
    """Преобразует байты в строку вида '20 MB'."""
    mb = size_bytes / (1024 * 1024)
    return f"{int(mb)} MB"


# ===== Работа с PRO через billing =====

def _is_pro_remote(user_id: int) -> Optional[bool]:
    """Запрос к /is-pro в billing-сервисе. True/False или None при ошибке."""
    if not BILLING_BASE_URL:
        logger.warning("BILLING_BASE_URL is not set; assuming FREE")
        return None

    url = f"{BILLING_BASE_URL.rstrip('/')}/is-pro"
    try:
        resp = requests.get(url, params={"user_id": user_id}, timeout=3)
        resp.raise_for_status()
        data = resp.json()
        logger.info("is_pro_remote(%s) -> %s", user_id, data)
        return bool(data.get("pro"))
    except Exception as e:
        logger.error("Failed to call %s: %s", url, e)
        return None


def is_pro(user_id: int) -> bool:
    """
    ЕДИНСТВЕННАЯ функция проверки PRO в боте.
    Истина берётся из billing-сервиса.
    """
    res = _is_pro_remote(user_id)
    if res is None:
        # при ошибке считаем FREE, чтобы не ломать работу бота
        return False
    return res


def get_user_limit(user_id: int) -> int:
    """Лимит размера файла с учётом тарифа."""
    return PRO_MAX_SIZE if is_pro(user_id) else FREE_MAX_SIZE
import os
import logging
from typing import Optional
from pathlib import Path

import requests

# ========== LOGGING ==========
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ========== PATHS ==========
BASE_DIR = Path(__file__).resolve().parent

# Папка для файлов, с которыми работает бот
FILES_DIR = BASE_DIR / "files"
TMP_DIR = BASE_DIR / "tmp"

FILES_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# ========== BOT CONFIG ==========
# Токен бота из переменной окружения BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN is not set in environment")

# username бота без @ — нужен для deeplink и HTML-страниц биллинга
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")

# ========== LIMITS ==========
FREE_MAX_SIZE = 20 * 1024 * 1024  # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024  # 100 MB


def format_mb(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    return f"{int(mb)} MB"


# ========== BILLING SERVICE ==========
# В pdfbot-staging в Railway:
#  APP_BASE_URL=https://pdfbot-billing-production.up.railway.app
#  (можешь также добавить BILLING_BASE_URL, но не обязательно)
BILLING_BASE_URL = (
    os.getenv("BILLING_BASE_URL")
    or os.getenv("APP_BASE_URL")  # fallback на уже существующую переменную
)

if not BILLING_BASE_URL:
    logger.error("BILLING_BASE_URL / APP_BASE_URL not set; PRO check will fail")


# ========== PRO CHECK ==========
def _is_pro_remote(user_id: int) -> Optional[bool]:
    """
    GET {BILLING_BASE_URL}/is-pro?user_id=...
    Возвращает True/False или None при ошибке.
    """
    if not BILLING_BASE_URL:
        return None

    url = f"{BILLING_BASE_URL.rstrip('/')}/is-pro"
    try:
        resp = requests.get(url, params={"user_id": user_id}, timeout=3)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Billing is-pro(%s) -> %s", user_id, data)
        return bool(data.get("pro"))
    except Exception as e:
        logger.error("Error calling billing /is-pro: %s", e)
        return None


def is_pro(user_id: int) -> bool:
    """
    Единственный источник истины — billing-сервис.
    """
    result = _is_pro_remote(user_id)
    return bool(result)


def get_user_limit(user_id: int) -> int:
    """
    Возвращает лимит по тарифу.
    """
    return PRO_MAX_SIZE if is_pro(user_id) else FREE_MAX_SIZE
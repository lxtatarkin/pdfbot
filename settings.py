# settings.py
import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from db import is_user_pro, get_subscription  # проверка PRO и данные из PostgreSQL

# ========== LOGGING ==========
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ========== PATHS ==========
BASE_DIR = Path(__file__).resolve().parent

FILES_DIR = BASE_DIR / "files"
TMP_DIR = BASE_DIR / "tmp"

FILES_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# ========== BOT CONFIG ==========
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN is not set in environment")

BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")

# ========== LIMITS ==========
FREE_MAX_SIZE = 20 * 1024 * 1024  # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024  # 100 MB


def format_mb(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    return f"{int(mb)} MB"


# ========== PRO SUBSCRIPTIONS (через PostgreSQL) ==========

async def get_pro_expire_ts(user_id: int) -> Optional[int]:
    """
    Возвращает timestamp окончания PRO или None, если подписки нет/истекла.
    Обёртка над get_subscription из db.py для совместимости со старым кодом.
    """
    sub = await get_subscription(user_id)
    if not sub:
        return None

    expires_at = sub.get("expires_at")
    if not isinstance(expires_at, datetime):
        return None

    # гарантируем UTC и возвращаем UNIX timestamp (int)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return int(expires_at.timestamp())


async def is_pro(user_id: int) -> bool:
    """
    Проверка PRO-статуса пользователя через PostgreSQL.
    """
    return await is_user_pro(user_id)


async def get_user_limit(user_id: int) -> int:
    """
    Возвращает лимит по тарифу через PostgreSQL.
    """
    if await is_user_pro(user_id):
        return PRO_MAX_SIZE
    return FREE_MAX_SIZE

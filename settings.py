# settings.py
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

from db import (
    add_subscription_months,  # продление подписки
    get_subscription,         # получение данных подписки
)

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
# Телеграм жёстко ограничивает загрузку файлов пользователем в бота до 20 МБ.
# Поэтому и FREE, и PRO имеют одинаковый лимит по размеру файла.
FREE_MAX_SIZE = 20 * 1024 * 1024  # 20 MB
PRO_MAX_SIZE = 20 * 1024 * 1024   # 20 MB (ограничение Telegram)


def format_mb(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    return f"{int(mb)} MB"


# ========== PRO SUBSCRIPTIONS (PostgreSQL) ==========

async def is_pro(user_id: int) -> bool:
    """
    Проверка PRO-статуса пользователя по данным в PostgreSQL.
    PRO только если tier='PRO' и expires_at > сейчас.
    """
    sub = await get_subscription(user_id)
    if not sub:
        return False

    if sub.get("tier") != "PRO":
        return False

    expires_at = sub.get("expires_at")
    if not expires_at:
        return False

    # нормализуем таймзону
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    return expires_at > now


async def get_user_limit(user_id: int) -> int:
    """
    Асинхронно возвращает лимит по тарифу.
    Использует is_pro, чтобы учитывать срок действия подписки.
    Сейчас размер файла одинаковый для всех, лимит задаётся Telegram.
    """
    if await is_pro(user_id):
        return PRO_MAX_SIZE
    return FREE_MAX_SIZE


async def get_pro_expire_ts(user_id: int) -> int | None:
    """
    Возвращает timestamp (int, seconds) окончания PRO
    или None, если подписки нет или она истекла.
    """
    sub = await get_subscription(user_id)
    if not sub:
        return None

    if sub.get("tier") != "PRO":
        return None

    expires_at = sub.get("expires_at")
    if not expires_at:
        return None

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    if expires_at <= now:
        return None

    return int(expires_at.timestamp())


async def extend_pro(user_id: int, days: int) -> int:
    """
    Обёртка над PostgreSQL для продления подписки.
    В старом коде, возможно, вызывалась extend_pro(user_id, 30/90/365).
    Здесь переводим дни в месяцы: days / 30 (грубо, для совместимости).
    """
    if days <= 0:
        raise ValueError("days must be > 0")

    # Грубо переводим дни в месяцы
    months = max(1, round(days / 30))

    # plan и payment_id можно потом заполнять реальными значениями
    expires_dt = await add_subscription_months(
        user_id=user_id,
        months=months,
        plan=f"{months}m",
        payment_id=None,
    )
    if expires_dt.tzinfo is None:
        expires_dt = expires_dt.replace(tzinfo=timezone.utc)

    return int(expires_dt.timestamp())
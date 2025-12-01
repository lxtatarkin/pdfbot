# settings.py
import os
import logging
from pathlib import Path
from datetime import timezone

from db import (
    is_user_pro,            # проверка PRO-статуса
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
FREE_MAX_SIZE = 20 * 1024 * 1024  # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024  # 100 MB


def format_mb(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    return f"{int(mb)} MB"


# ========== PRO SUBSCRIPTIONS (через PostgreSQL) ==========

async def is_pro(user_id: int) -> bool:
    """
    Асинхронная проверка PRO-статуса пользователя через PostgreSQL.
    Совместимо с прежним интерфейсом.
    """
    return await is_user_pro(user_id)


async def get_user_limit(user_id: int) -> int:
    """
    Асинхронно возвращает лимит по тарифу.
    Совместимо с прежним интерфейсом.
    """
    if await is_user_pro(user_id):
        return PRO_MAX_SIZE
    return FREE_MAX_SIZE


async def get_pro_expire_ts(user_id: int) -> int | None:
    """
    Совместимая с прошлой версией функция:
    возвращает timestamp (int, seconds) окончания PRO
    или None, если подписки нет/истекла.
    """
    sub = await get_subscription(user_id)
    if not sub:
        return None

    if sub.get("tier") != "PRO":
        return None

    expires_at = sub.get("expires_at")
    if not expires_at:
        return None

    # expires_at — это datetime из asyncpg (TIMESTAMPTZ)
    return int(expires_at.replace(tzinfo=timezone.utc).timestamp())


async def extend_pro(user_id: int, days: int) -> int:
    """
    Совместимая обёртка над PostgreSQL:
    раньше было "продлить на N дней", сейчас — переведём дни в месяцы условно.

    Если в pro.py ты вызываешь extend_pro(user_id, 30/90/365),
    можно либо:
      – там переделать на месяцы,
      – либо здесь грубо конвертировать: days / 30.
    Для совместимости сделаем простую конверсию.
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
    return int(expires_dt.replace(tzinfo=timezone.utc).timestamp())
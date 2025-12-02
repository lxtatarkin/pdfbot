# db.py
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import asyncpg

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """
    Ленивая инициализация пула подключений.
    """
    global _pool

    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")

        logger.info("Creating Postgres pool...")
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

    return _pool


async def init_db() -> None:
    """
    Создаёт таблицы для подписок и промокодов, если их ещё нет.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("SET TIME ZONE 'UTC';")

        # Таблица подписок
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id       BIGINT PRIMARY KEY,
                tier          TEXT NOT NULL,
                expires_at    TIMESTAMPTZ NOT NULL,
                last_plan     TEXT,
                last_payment  TEXT,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )

        # Таблица промокодов
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS promo_codes (
                code         TEXT PRIMARY KEY,
                months       INTEGER NOT NULL,
                max_uses     INTEGER NOT NULL,
                used_count   INTEGER NOT NULL DEFAULT 0,
                is_active    BOOLEAN NOT NULL DEFAULT TRUE,
                expires_at   TIMESTAMPTZ,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )

        # Кто использовал какой код (лог)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS promo_redemptions (
                id           BIGSERIAL PRIMARY KEY,
                code         TEXT NOT NULL REFERENCES promo_codes(code) ON DELETE CASCADE,
                user_id      BIGINT NOT NULL,
                redeemed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (code, user_id)
            );
            """
        )

        logger.info("Database schema ensured (subscriptions + promo_codes).")


async def close_db() -> None:
    """
    Аккуратно закрыть пул при остановке бота.
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Postgres pool closed")


# ====== ЛОГИКА ПОДПИСОК ======

async def add_subscription_months(
    user_id: int,
    months: int,
    plan: Optional[str] = None,
    payment_id: Optional[str] = None,
):
    """
    Продлить подписку на N месяцев.
    """
    if months <= 0:
        raise ValueError("months must be > 0")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO subscriptions (user_id, tier, expires_at, last_plan, last_payment)
            VALUES (
                $1,
                'PRO',
                now() + $2 * INTERVAL '1 month',
                $3,
                $4
            )
            ON CONFLICT (user_id) DO UPDATE
            SET
                tier = 'PRO',
                expires_at = GREATEST(subscriptions.expires_at, now()) + $2 * INTERVAL '1 month',
                last_plan = $3,
                last_payment = $4,
                updated_at = now()
            RETURNING expires_at;
            """,
            user_id,
            months,
            plan,
            payment_id,
        )
        return row["expires_at"]


async def get_subscription(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Вернуть данные подписки.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, tier, expires_at, last_plan, last_payment
            FROM subscriptions
            WHERE user_id = $1;
            """,
            user_id,
        )

    if not row:
        return None

    return {
        "user_id": row["user_id"],
        "tier": row["tier"],
        "expires_at": row["expires_at"],
        "last_plan": row["last_plan"],
        "last_payment": row["last_payment"],
    }


async def is_user_pro(user_id: int) -> bool:
    """
    True, если подписка активна.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT tier, expires_at
            FROM subscriptions
            WHERE user_id = $1;
            """,
            user_id,
        )

    if not row:
        return False

    if row["tier"] != "PRO":
        return False

    now_utc = datetime.now(timezone.utc)
    return row["expires_at"] > now_utc
# db.py
import os
import logging
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """
    Ленивая инициализация пула подключений.
    Вызываем этот метод везде, где нужна БД.
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
    Вызываем один раз при старте бота.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Включим расширение для таймзон, если его нет (на всякий случай)
        await conn.execute("SET TIME ZONE 'UTC';")

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id       BIGINT PRIMARY KEY,
                tier          TEXT NOT NULL,              -- например 'PRO'
                expires_at    TIMESTAMPTZ NOT NULL,       -- когда истекает подписка
                last_plan     TEXT,                       -- 'month' | 'quarter' | 'year'
                last_payment  TEXT,                       -- id транзакции/покупки в Stars (строка)
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS promo_codes (
                code         TEXT PRIMARY KEY,            -- сам промокод
                months       INTEGER NOT NULL,            -- на сколько месяцев даёт подписку
                max_uses     INTEGER NOT NULL,            -- сколько всего раз можно использовать
                used_count   INTEGER NOT NULL DEFAULT 0,  -- сколько уже использовали
                is_active    BOOLEAN NOT NULL DEFAULT TRUE,
                expires_at   TIMESTAMPTZ,                 -- опциональная дата окончания действия кода
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS promo_redemptions (
                id           BIGSERIAL PRIMARY KEY,
                code         TEXT NOT NULL REFERENCES promo_codes(code) ON DELETE CASCADE,
                user_id      BIGINT NOT NULL,
                redeemed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (code, user_id)                    -- один код один раз на пользователя
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
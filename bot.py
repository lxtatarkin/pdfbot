# bot.py
import asyncio

from aiogram import Bot, Dispatcher

from settings import TOKEN, logger
from handlers import routers  # берем список роутеров
from db import init_db, close_db  # инициализация и закрытие PostgreSQL

async def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set in environment")
        return

    # 1) Инициализируем БД (создаём таблицы, пул соединений и т.д.)
    await init_db()

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Подключаем все роутеры из списка
    for router in routers:
        dp.include_router(router)

    logger.info("Bot started")

    try:
        # 2) Стартуем polling
        await dp.start_polling(bot)
    finally:
        # 3) Корректно закрываем пул подключений к БД
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
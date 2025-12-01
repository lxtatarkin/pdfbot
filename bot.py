import asyncio

from aiogram import Bot, Dispatcher

from settings import TOKEN, logger
from handlers import routers
from db import init_db, close_db   # <-- добавили


async def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set in environment")
        return

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Подключаем все роутеры
    for router in routers:
        dp.include_router(router)

    # ---- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ----
    await init_db()
    logger.info("Database initialized")

    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    finally:
        # ---- Корректное закрытие пула БД ----
        await close_db()
        logger.info("DB pool closed, bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
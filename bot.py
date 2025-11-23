import asyncio

from aiogram import Bot, Dispatcher

from settings import TOKEN, logger
from handlers import routers  # берем список роутеров


async def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set in environment")
        return

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Подключаем все роутеры из списка
    for router in routers:
        dp.include_router(router)

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
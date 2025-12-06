# utils.py
from typing import Optional

from aiogram import types

from settings import get_user_limit, is_pro, format_mb, logger


async def check_size_or_reject(
    message: types.Message,
    size_bytes: Optional[int],
) -> bool:
    """
    Проверяем размер файла относительно лимита пользователя.
    Если файл больше лимита — отправляем сообщение и возвращаем False.
    Если всё ок — возвращаем True.
    """
    user_id = message.from_user.id

    # асинхронные функции вызываем через await
    max_size = await get_user_limit(user_id)
    pro = await is_pro(user_id)
    tier = "PRO" if pro else "FREE"

    if size_bytes is not None and size_bytes > max_size:
        await message.answer(
            "Файл слишком большой.\n"
            f"Лимит Telegram: {format_mb(max_size)} на файл.\n\n"
            "Пожалуйста, уменьшите размер файла (сжатие или разделение) "
            "и отправьте его снова."
        )
        logger.info(
            f"User {user_id} exceeded size limit: file={size_bytes}, limit={max_size}, tier={tier}"
        )
        return False

    return True


async def ensure_pro(message: types.Message) -> bool:
    """
    Универсальная проверка PRO.
    Возвращает True, если PRO активен.
    Если нет — отправляет сообщение и возвращает False.
    """
    user_id = message.from_user.id
    pro = await is_pro(user_id)

    if not pro:
        await message.answer(
            "Ваш PRO не активен или закончился.\n"
            "Оформите или продлите подписку через /pro."
        )
        logger.info(f"User {user_id} tried PRO feature without active subscription")
        return False

    return True
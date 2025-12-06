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
            f"User {user_id} exceeded size limit: "
            f"file={size_bytes}, limit={max_size}, tier={tier}"
        )
        return False

    return True


async def ensure_pro(message: types.Message) -> bool:
    """
    Универсальная проверка PRO.
    Возвращает True, если PRO активен.
    Если нет — отправляет сообщение и возвращает False.

    Важно: в callback-хендлерах часто передают message, созданный ботом
    (callback.message). В этом случае message.from_user — это бот, а не
    реальный пользователь. Тогда берём user_id из message.chat.id.
    """
    user_id = message.from_user.id

    # Если это сообщение отправлено ботом (как в callback.message),
    # используем chat.id как идентификатор пользователя (в личке это user_id).
    if getattr(message.from_user, "is_bot", False) and message.chat:
        user_id = message.chat.id

    pro = await is_pro(user_id)

    if not pro:
        await message.answer(
            "Ваш PRO не активен или закончился.\n"
            "Оформите или продлите подписку через /pro."
        )
        logger.info(
            f"User {user_id} tried PRO feature without active subscription"
        )
        return False

    return True
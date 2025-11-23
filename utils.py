# utils.py
from typing import Optional

from aiogram import types

from settings import get_user_limit, is_pro, format_mb, logger


async def check_size_or_reject(
    message: types.Message,
    size_bytes: Optional[int],
) -> bool:
    user_id = message.from_user.id
    max_size = get_user_limit(user_id)
    tier = "PRO" if is_pro(user_id) else "FREE"

    if size_bytes is not None and size_bytes > max_size:
        await message.answer(
            f"Файл слишком большой для тарифа ({tier}).\n"
            f"Лимит: {format_mb(max_size)}.\n\n"
            "Для больших файлов нужен PRO.\n"
            "Смотрите /pro."
        )
        logger.info(
            f"User {user_id} exceeded size limit: file={size_bytes}, limit={max_size}"
        )
        return False

    return True


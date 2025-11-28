# handlers/merge_done.py
from pathlib import Path

from aiogram import Router, types, F
from PyPDF2 import PdfMerger

from settings import FILES_DIR, logger
from state import user_modes, user_merge_files
from i18n import t

router = Router()

@router.callback_query(F.data == "merge:confirm")
async def merge_confirm(callback: types.CallbackQuery):
    """
    Новый способ — по нажатию inline-кнопки «Объединить».
    """
    user_id = callback.from_user.id
    mode = user_modes.get(user_id, "compress")

    if mode != "merge":
        await callback.answer()
        return

    await callback.answer()
    await _run_merge(user_id, callback.message)

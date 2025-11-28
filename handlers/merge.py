# handlers/merge_done.py
from pathlib import Path

from aiogram import Router, types, F
from PyPDF2 import PdfMerger

from settings import FILES_DIR, logger
from state import user_modes, user_merge_files
from i18n import t

router = Router()

async def _run_merge(user_id: int, message: types.Message) -> None:
    files_list = user_merge_files.get(user_id, [])

    if len(files_list) < 2:
        await message.answer(t(user_id, "merge_need_two"))
        return

    await message.answer(t(user_id, "merge_start", count=len(files_list)))

    merged_name = Path(files_list[0]).stem + "_merged.pdf"
    merged_path = FILES_DIR / merged_name

    try:
        merger = PdfMerger()
        for p in files_list:
            merger.append(str(p))
        merger.write(str(merged_path))
        merger.close()
    except Exception as e:
        logger.error(f"Merge error for user {user_id}: {e}")
        await message.answer(t(user_id, "merge_error"))
        return

    await message.answer_document(
        types.FSInputFile(merged_path),
        caption=t(user_id, "msg_done"),
    )

    user_merge_files[user_id] = []


@router.callback_query(F.data == "merge:confirm")
async def merge_confirm(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    mode = user_modes.get(user_id, "compress")

    if mode != "merge":
        await callback.answer()
        return

    await callback.answer()
    await _run_merge(user_id, callback.message)

# handlers/merge_done.py
from pathlib import Path

from aiogram import Router, types, F
from PyPDF2 import PdfMerger

from settings import FILES_DIR, logger
from state import user_modes, user_merge_files
from i18n import t

router = Router()


@router.message(F.text)
async def merge_done(message: types.Message):
    """
    Обработка команды «Готово» в режиме объединения PDF.
    """
    user_id = message.from_user.id
    mode = user_modes.get(user_id, "compress")

    text_raw = (message.text or "").strip()
    text_val = text_raw.lower()

    # Реакция только в режиме merge
    if mode != "merge":
        return

    # Разрешённые команды завершения
    finish_commands = ("готово", "done", "/done", "/merge")
    if text_val not in finish_commands:
        return

    files_list = user_merge_files.get(user_id, [])

    if len(files_list) < 2:
        await message.answer(t(user_id, "merge_need_two"))
        return

    await message.answer(
        t(user_id, "merge_start", count=len(files_list))
    )

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
        caption=t(user_id, "msg_done")
    )

    # очищаем список файлов
    user_merge_files[user_id] = []

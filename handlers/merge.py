from pathlib import Path

from aiogram import Router, types, F
from PyPDF2 import PdfMerger

from settings import FILES_DIR, logger
from state import user_modes, user_merge_files

router = Router()


@router.message(F.text)
async def merge_done(message: types.Message):
    """
    Обработка команды «Готово» в режиме объединения PDF.
    Предполагается, что сами PDF-файлы уже добавлены в user_merge_files[user_id]
    в хендлере, который принимает документы (mode == "merge").
    """
    user_id = message.from_user.id
    mode = user_modes.get(user_id, "compress")

    text_raw = (message.text or "").strip()
    text_val = text_raw.lower()

    # Обрабатываем только если пользователь в режиме merge и написал "готово"/"/done"/"/merge"
    if mode != "merge":
        return

    if text_val not in ("готово", "/done", "/merge"):
        return

    files_list = user_merge_files.get(user_id, [])

    if len(files_list) < 2:
        await message.answer("Добавьте минимум 2 PDF.")
        return

    await message.answer(f"Объединяю {len(files_list)} PDF...")

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
        await message.answer("Ошибка при объединении.")
        return

    await message.answer_document(
        types.FSInputFile(merged_path),
        caption="Готово!"
    )

    # очищаем список файлов для объединения
    user_merge_files[user_id] = []

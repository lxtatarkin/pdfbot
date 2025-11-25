# handlers/doc_image.py
from pathlib import Path

from aiogram import Router, types, F, Bot

from settings import (
    get_user_limit,
    is_pro,
    format_mb,
    FILES_DIR,
    logger,
)

from i18n import t  # ЛОКАЛИЗАЦИЯ
from pdf_services import (
    image_file_to_pdf,
    office_doc_to_pdf,
)

router = Router()


async def check_size_or_reject(message: types.Message, size_bytes: int | None) -> bool:
    """Проверка лимита размера файла для FREE/PRO."""
    user_id = message.from_user.id
    max_size = get_user_limit(user_id)
    tier = "PRO" if is_pro(user_id) else "FREE"

    if size_bytes is not None and size_bytes > max_size:
        await message.answer(
            t(
                user_id,
                "err_file_too_big",
                tier=tier,
                limit=format_mb(max_size)
            )
        )
        logger.info(
            f"User {user_id} exceeded size limit: file={size_bytes}, limit={max_size}"
        )
        return False

    return True


@router.message(F.document & (F.document.mime_type != "application/pdf"))
async def handle_doc(message: types.Message, bot: Bot):
    """
    Обработка документов и изображений, присланных как файл:
    - изображения -> PDF
    - DOC/DOCX/XLS/XLSX/PPT/PPTX -> PDF
    """
    user_id = message.from_user.id
    doc_msg = message.document
    filename = doc_msg.file_name or "file"
    ext = filename.split(".")[-1].lower()

    # проверка лимита
    if not await check_size_or_reject(message, doc_msg.file_size):
        return

    # =============== IMAGE AS FILE ===============
    if doc_msg.mime_type and doc_msg.mime_type.startswith("image/"):
        await message.answer(t(user_id, "msg_converting_image"))

        file = await bot.get_file(doc_msg.file_id)
        src_path = FILES_DIR / filename
        await bot.download_file(file.file_path, destination=src_path)

        pdf_path = image_file_to_pdf(src_path)
        if not pdf_path:
            await message.answer(t(user_id, "err_image_convert"))
            return

        await message.answer_document(
            types.FSInputFile(pdf_path),
            caption=t(user_id, "msg_done")
        )
        return

    # =============== OFFICE DOCS ===============
    supported = {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}
    if ext not in supported:
        await message.answer(t(user_id, "err_unsupported"))
        return

    await message.answer(t(user_id, "msg_converting_doc"))

    file = await bot.get_file(doc_msg.file_id)
    src_path = FILES_DIR / filename
    await bot.download_file(file.file_path, destination=src_path)

    pdf_path = office_doc_to_pdf(src_path)
    if not pdf_path:
        await message.answer(t(user_id, "err_doc_convert"))
        return

    await message.answer_document(
        types.FSInputFile(pdf_path),
        caption=t(user_id, "msg_done")
    )

from aiogram import Router, types, F, Bot

from settings import FILES_DIR
from pdf_services import image_file_to_pdf, office_doc_to_pdf
from utils import check_size_or_reject

router = Router()

    @router.message(F.document & (F.document.mime_type != "application/pdf"))
    async def handle_doc(message: types.Message, bot: Bot):
        doc_msg = message.document
        filename = doc_msg.file_name or "file"
        ext = filename.split(".")[-1].lower()

        # size check
        if not await check_size_or_reject(message, doc_msg.file_size):
            return

        # IMAGE AS FILE
        if doc_msg.mime_type and doc_msg.mime_type.startswith("image/"):
            await message.answer("Конвертирую изображение в PDF...")

            file = await bot.get_file(doc_msg.file_id)
            src_path = FILES_DIR / filename
            await bot.download_file(file.file_path, destination=src_path)

            pdf_path = image_file_to_pdf(src_path)
            if not pdf_path:
                await message.answer("Не удалось конвертировать изображение.")
                return

            await message.answer_document(types.FSInputFile(pdf_path), caption="Готово.")
            return

        # OFFICE DOCS
        supported = {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}
        if ext not in supported:
            await message.answer(
                "Этот тип пока не поддерживается.\n"
                "Поддержка: DOC, DOCX, XLS, XLSX, PPT, PPTX и изображения."
            )
            return

        await message.answer("Конвертирую в PDF...")

        file = await bot.get_file(doc_msg.file_id)
        src_path = FILES_DIR / filename
        await bot.download_file(file.file_path, destination=src_path)

        pdf_path = office_doc_to_pdf(src_path)
        if not pdf_path:
            await message.answer("Ошибка при конвертации документа в PDF.")
            return

        await message.answer_document(types.FSInputFile(pdf_path), caption="Готово.")
        return
# handlers/pdf.py
from pathlib import Path
import zipfile

from aiogram import Router, types, F, Bot
from PyPDF2 import PdfReader, PdfWriter

from settings import (
    get_user_limit,
    is_pro,
    format_mb,
    FILES_DIR,
    logger,
)
from state import (
    user_modes,
    user_merge_files,
    user_watermark_state,
    user_pages_state,
)
from keyboards import get_pages_menu_keyboard
from pdf_services import (
    ocr_pdf_to_txt,
    create_searchable_pdf,
    split_pdf_to_pages,
    extract_text_from_pdf,
    compress_pdf,
)

router = Router()


async def check_size_or_reject(message: types.Message, size_bytes: int | None) -> bool:
    """Проверка лимита размера файла для FREE/PRO."""
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


@router.message(F.document & (F.document.mime_type == "application/pdf"))
async def handle_pdf(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    mode = user_modes.get(user_id, "compress")
    doc_msg = message.document

    # Проверка размера
    if not await check_size_or_reject(message, doc_msg.file_size):
        return

    # Скачиваем PDF во временную папку
    file = await bot.get_file(doc_msg.file_id)
    src_path = FILES_DIR / doc_msg.file_name
    await bot.download_file(file.file_path, destination=src_path)

    # =============================
    # РЕДАКТОР СТРАНИЦ: новый PDF
    # =============================
    if mode.startswith("pages"):
        if not is_pro(user_id):
            await message.answer("Редактор страниц доступен только для PRO-пользователей. См. /pro")
            return

        try:
            reader = PdfReader(str(src_path))
            num_pages = len(reader.pages)
        except Exception as e:
            logger.error(f"Pages editor open error: {e}")
            await message.answer("Не удалось открыть PDF.")
            return

        user_pages_state[user_id] = {
            "pdf_path": src_path,
            "pages": num_pages,
        }
        user_modes[user_id] = "pages_menu"

        await message.answer(
            f"Редактор страниц PDF.\n"
            f"Файл: {doc_msg.file_name}\n"
            f"Страниц в документе: {num_pages}\n\n"
            "Выбери действие:",
            reply_markup=get_pages_menu_keyboard()
        )
        return

    # =============================
    # PRO: OCR ДЛЯ PDF
    # =============================
    if mode == "ocr":
        if not is_pro(user_id):
            await message.answer("OCR доступен только для PRO-пользователей. См. /pro")
            return

        await message.answer("Распознаю текст в PDF (OCR)...")

        txt_path = ocr_pdf_to_txt(src_path, user_id, lang="rus+eng")
        if not txt_path:
            await message.answer("Не удалось распознать текст (возможно очень плохое качество скана).")
            return

        await message.answer_document(
            types.FSInputFile(txt_path),
            caption="Готово: OCR-текст из PDF."
        )
        logger.info(f"OCR PDF done for user {user_id}")
        return

    # =============================
    # PRO: Searchable PDF
    # =============================
    if mode == "searchable_pdf":
        if not is_pro(user_id):
            await message.answer("Searchable PDF доступен только для PRO-пользователей. См. /pro")
            return

        await message.answer("Создаю searchable PDF (можно выделять текст)...")

        out_path = create_searchable_pdf(src_path, lang="rus+eng")
        if not out_path:
            await message.answer("Ошибка при создании searchable PDF.")
            return

        await message.answer_document(
            types.FSInputFile(out_path),
            caption="Готово: searchable PDF. Теперь текст можно выделять и искать."
        )
        logger.info(f"Searchable PDF done for user {user_id}")
        return

    # =============================
    # WATERMARK STEP 1: получить PDF
    # =============================
    if mode == "watermark":
        if not is_pro(user_id):
            await message.answer("Водяные знаки доступны только для PRO-пользователей. См. /pro")
            return

        user_watermark_state[user_id] = {"pdf_path": src_path}
        user_modes[user_id] = "watermark_wait_text"

        await message.answer(
            "PDF получил.\n"
            "Теперь отправь текст водяного знака.\n"
            "Например: CONFIDENTIAL, DRAFT, КОПИЯ."
        )
        return

    # =============================
    # MERGE MODE: просто копим PDF
    # =============================
    if mode == "merge":
        files_list = user_merge_files.setdefault(user_id, [])
        if len(files_list) >= 10:
            await message.answer("Можно объединить не больше 10 файлов за раз.")
            return

        files_list.append(src_path)
        await message.answer(
            f"Добавил файл #{len(files_list)} для объединения.\n"
            "Пришли ещё PDF или напиши «Готово», чтобы объединить."
        )
        return

    # =============================
    # PDF → TEXT
    # =============================
    if mode == "pdf_text":
        await message.answer("Извлекаю текст...")

        text_full = extract_text_from_pdf(src_path)
        if not text_full:
            await message.answer("Текста не найдено (возможно скан или ошибка чтения).")
            return

        txt_path = FILES_DIR / (Path(doc_msg.file_name).stem + ".txt")
        txt_path.write_text(text_full, encoding="utf-8")

        await message.answer_document(types.FSInputFile(txt_path), caption="Готово.")
        return

    # =============================
    # SPLIT PDF
    # =============================
    if mode == "split":
        await message.answer("Разделяю PDF...")

        pages = split_pdf_to_pages(src_path)
        if pages is None:
            await message.answer("Не удалось открыть PDF.")
            return

        if len(pages) <= 1:
            await message.answer("Там всего 1 страница.")
            return

        n = len(pages)

        if n <= 10:
            for i, p in enumerate(pages, start=1):
                await message.answer_document(
                    types.FSInputFile(p),
                    caption=f"Страница {i}/{n}"
                )
        else:
            zip_path = FILES_DIR / f"{src_path.stem}_pages.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in pages:
                    zf.write(p, arcname=p.name)

            await message.answer_document(
                types.FSInputFile(zip_path),
                caption=f"Готово: {n} страниц в ZIP."
            )
        return

    # =============================
    # COMPRESS PDF (DEFAULT)
    # =============================
    await message.answer("Сжимаю PDF...")
    compressed_path = FILES_DIR / f"compressed_{doc_msg.file_name}"

    ok = compress_pdf(src_path, compressed_path)
    if not ok:
        await message.answer("Не удалось сжать PDF (ошибка Ghostscript).")
        return

    await message.answer_document(types.FSInputFile(compressed_path), caption="Готово.")
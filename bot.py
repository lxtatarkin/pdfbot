import asyncio
import zipfile
import subprocess
from io import BytesIO
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from PyPDF2 import PdfReader, PdfMerger, PdfWriter
from settings import (
    TOKEN,
    is_pro,
    get_user_limit,
    format_mb,
    FILES_DIR,
    logger,
    PRO_MAX_SIZE,
)
from keyboards import (
    get_main_keyboard,
    get_pages_menu_keyboard,
    get_rotate_keyboard,
    get_watermark_keyboard,
)
from pdf_services import (
    apply_watermark,
    parse_page_range,
    rotate_page_inplace,
    ocr_pdf_to_txt,
    create_searchable_pdf,
    split_pdf_to_pages,
    merge_pdfs,
    extract_text_from_pdf,
    compress_pdf,
    image_file_to_pdf,
    office_doc_to_pdf,
)
from state import (
    user_modes,
    user_merge_files,
    user_watermark_state,
    user_pages_state,
)
from handlers.start import router as start_router

# ===== check size helper =====
async def check_size_or_reject(message: types.Message, size_bytes: int | None) -> bool:
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

# ==========================
#   MAIN
# ==========================
async def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set in environment")
        return

    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    router = Router()

    logger.info("Bot started")

    # ================================
    #   BUTTON MODES
    # ================================
    @router.message(F.text == "📉 Сжать PDF")
    async def mode_compress(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "compress"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer("Режим: сжатие PDF. Пришли PDF.", reply_markup=get_main_keyboard())

    @router.message(F.text == "📝 PDF → текст")
    async def mode_pdf_text(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "pdf_text"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer("Режим: PDF → текст. Пришли PDF.", reply_markup=get_main_keyboard())

    @router.message(F.text == "📄 Документ/фото → PDF")
    async def mode_doc_photo(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "doc_photo"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer(
            "Режим: DOC/IMG → PDF. Пришли документ или файл-изображение.",
            reply_markup=get_main_keyboard()
        )

    @router.message(F.text == "📎 Объединить PDF")
    async def mode_merge(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "merge"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer(
            "Режим: объединение.\n"
            "Пришли 2–10 PDF-файлов.\n"
            "Потом напиши «Готово».",
            reply_markup=get_main_keyboard()
        )

    @router.message(F.text == "✂️ Разделить PDF")
    async def mode_split(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "split"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer(
            "Режим: разделение PDF.\nПришли один PDF.",
            reply_markup=get_main_keyboard()
        )

    @router.message(F.text == "🔍 OCR")
    async def mode_ocr(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "ocr"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        if not is_pro(user_id):
            await message.answer(
                "Режим: 🔍 OCR (распознавание текста в сканах и фото).\n"
                "Эта функция доступна только для PRO-пользователей.\n\n"
                "Подробнее: /pro"
            )
        else:
            await message.answer(
                "Режим: 🔍 OCR.\n"
                "Пришли PDF-скан или изображение (фото/картинка). Я верну TXT-файл с распознанным текстом."
            )

    @router.message(F.text == "📑 Searchable PDF")
    async def mode_searchable_pdf(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "searchable_pdf"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        if not is_pro(user_id):
            await message.answer(
                "Режим: 📑 Searchable PDF.\n"
                "Делаю из скана PDF с выделяемым текстом.\n"
                "Функция доступна только для PRO-пользователей.\n\n"
                "Подробнее: /pro"
            )
        else:
            await message.answer(
                "Режим: 📑 Searchable PDF.\n"
                "Пришли сканированный PDF. Я верну PDF, в котором текст можно выделять и искать."
            )

    @router.message(F.text == "🧩 Редактор страниц")
    async def mode_pages(message: types.Message):
        user_id = message.from_user.id
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}

        if not is_pro(user_id):
            user_modes[user_id] = "compress"
            await message.answer(
                "Режим: 🧩 Редактор страниц PDF.\n"
                "Доступно только для PRO-пользователей.\n\n"
                "В этом режиме можно поворачивать, удалять и извлекать страницы.\n"
                "Подробнее: /pro"
            )
        else:
            user_modes[user_id] = "pages_wait_pdf"
            await message.answer(
                "Режим: 🧩 Редактор страниц PDF.\n"
                "Пришли PDF, страницы которого нужно отредактировать.",
                reply_markup=get_main_keyboard()
            )

    @router.message(F.text == "🛡 Водяной знак")
    async def mode_watermark(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "watermark"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}

        if not is_pro(user_id):
            await message.answer(
                "Режим: 🛡 водяной знак для PDF.\n"
                "Функция доступна только для PRO-пользователей.\n\n"
                "Подробнее: /pro"
            )
        else:
            await message.answer(
                "Режим: 🛡 Водяной знак.\n"
                "1) Пришли PDF-файл.\n"
                "2) Потом введи текст водяного знака.\n"
                "3) Выбери позицию на сетке и при желании включи Mosaic."
            )

    # ================================
    #   HANDLE PDF
    # ================================
    @router.message(F.document & (F.document.mime_type == "application/pdf"))
    async def handle_pdf(message: types.Message, bot: Bot):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "compress")
        doc_msg = message.document

        # size check
        if not await check_size_or_reject(message, doc_msg.file_size):
            return

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
                import zipfile  # можешь оставить импорт вверху, тогда эту строку не нужно
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
        return

    # ================================
    #   DOC / IMAGE → PDF
    # ================================
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

    # ================================
    #   TEXT COMMANDS (PAGES + MERGE + WATERMARK)
    # ================================
    @router.message(F.text)
    async def handle_text(message: types.Message):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "compress")
        text_raw = (message.text or "").strip()
        text_val = text_raw.lower()

        # ===== РЕДАКТОР СТРАНИЦ: ввод диапазона для ПОВОРОТА =====
        if mode == "pages_rotate_wait_pages":
            state = user_pages_state.get(user_id) or {}
            pdf_path = state.get("pdf_path")
            num_pages = state.get("pages")

            if not pdf_path or not Path(pdf_path).exists() or not num_pages:
                await message.answer("Нет загруженного PDF. Сначала выбери 🧩 Редактор страниц и пришли файл.")
                user_modes[user_id] = "compress"
                return

            if text_val == "all":
                pages = list(range(1, num_pages + 1))
            else:
                pages = parse_page_range(text_raw, num_pages)

            if not pages:
                await message.answer(
                    "Не удалось распознать страницы.\n"
                    "Примеры: 2, 1-3, 1,3,5-7 или all."
                )
                return

            state["rotate_pages"] = pages
            user_pages_state[user_id] = state
            user_modes[user_id] = "pages_rotate_wait_angle"

            await message.answer(
                f"Страницы для поворота: {text_raw}.\n"
                "Теперь выбери угол поворота:",
                reply_markup=get_rotate_keyboard()
            )
            return

        # ===== РЕДАКТОР СТРАНИЦ: ожидание угла (просим пользоваться кнопками) =====
        if mode == "pages_rotate_wait_angle":
            await message.answer("Выбери угол поворота с помощью кнопок под предыдущим сообщением.")
            return

        # ===== РЕДАКТОР СТРАНИЦ: ввод диапазона для УДАЛЕНИЯ =====
        if mode == "pages_delete_wait_pages":
            state = user_pages_state.get(user_id) or {}
            pdf_path = state.get("pdf_path")
            num_pages = state.get("pages")

            if not pdf_path or not Path(pdf_path).exists() or not num_pages:
                await message.answer("Нет загруженного PDF. Сначала выбери 🧩 Редактор страниц и пришли файл.")
                user_modes[user_id] = "compress"
                return

            pages = parse_page_range(text_raw, num_pages)
            if not pages:
                await message.answer(
                    "Не удалось распознать страницы для удаления.\n"
                    "Примеры: 2, 1-3, 1,3,5-7."
                )
                return

            delete_set = set(pages)

            try:
                reader = PdfReader(str(pdf_path))
            except Exception as e:
                logger.error(f"Pages delete open error: {e}")
                await message.answer("Не удалось открыть PDF.")
                return

            writer = PdfWriter()
            kept = 0
            for idx, page in enumerate(reader.pages, start=1):
                if idx in delete_set:
                    continue
                writer.add_page(page)
                kept += 1

            if kept == 0:
                await message.answer("После удаления не осталось ни одной страницы. Операция отменена.")
                user_modes[user_id] = "pages_menu"
                return

            out_path = FILES_DIR / f"{Path(pdf_path).stem}_deleted.pdf"
            try:
                with open(out_path, "wb") as f:
                    writer.write(f)
            except Exception as e:
                logger.error(f"Pages delete write error: {e}")
                await message.answer("Ошибка при сохранении PDF после удаления страниц.")
                return

            await message.answer_document(
                types.FSInputFile(out_path),
                caption=f"Готово: удалены страницы {text_raw}. Осталось страниц: {kept}."
            )

            user_pages_state[user_id] = {
                "pdf_path": out_path,
                "pages": kept,
            }
            user_modes[user_id] = "pages_menu"

            await message.answer(
                "Можно продолжить редактирование страниц:\n"
                "— Поворот\n"
                "— Удаление\n"
                "— Извлечение\n\n"
                "Выбери действие:",
                reply_markup=get_pages_menu_keyboard()
            )
            return

        # ===== РЕДАКТОР СТРАНИЦ: ввод диапазона для ИЗВЛЕЧЕНИЯ =====
        if mode == "pages_extract_wait_pages":
            state = user_pages_state.get(user_id) or {}
            pdf_path = state.get("pdf_path")
            num_pages = state.get("pages")

            if not pdf_path or not Path(pdf_path).exists() or not num_pages:
                await message.answer("Нет загруженного PDF. Сначала выбери 🧩 Редактор страниц и пришли файл.")
                user_modes[user_id] = "compress"
                return

            if text_val == "all":
                pages = list(range(1, num_pages + 1))
            else:
                pages = parse_page_range(text_raw, num_pages)

            if not pages:
                await message.answer(
                    "Не удалось распознать страницы для извлечения.\n"
                    "Примеры: 2, 1-3, 1,3,5-7 или all."
                )
                return

            try:
                reader = PdfReader(str(pdf_path))
            except Exception as e:
                logger.error(f"Pages extract open error: {e}")
                await message.answer("Не удалось открыть PDF.")
                return

            writer = PdfWriter()
            for p in pages:
                writer.add_page(reader.pages[p - 1])

            safe_suffix = text_raw.replace(",", "_").replace("-", "_").replace(" ", "")
            out_path = FILES_DIR / f"{Path(pdf_path).stem}_extract_{safe_suffix}.pdf"
            try:
                with open(out_path, "wb") as f:
                    writer.write(f)
            except Exception as e:
                logger.error(f"Pages extract write error: {e}")
                await message.answer("Ошибка при сохранении извлечённых страниц.")
                return

            await message.answer_document(
                types.FSInputFile(out_path),
                caption=f"Готово: извлечены страницы {text_raw} в отдельный PDF."
            )

            # основной документ не меняем
            user_modes[user_id] = "pages_menu"
            await message.answer(
                "Можно продолжить редактирование исходного файла.\n"
                "Выбери действие:",
                reply_markup=get_pages_menu_keyboard()
            )
            return

        # ===== ВОДЯНОЙ ЗНАК: шаг 2 — текст =====
        if mode == "watermark_wait_text":
            state = user_watermark_state.get(user_id) or {}
            pdf_path = state.get("pdf_path")

            if not pdf_path or not Path(pdf_path).exists():
                await message.answer("Не нашёл PDF для водяного знака. Начни заново и пришли PDF.")
                user_modes[user_id] = "watermark"
                user_watermark_state[user_id] = {}
                return

            wm_text = (message.text or "").strip()
            if not wm_text:
                await message.answer("Текст пустой. Отправь текст водяного знака ещё раз.")
                return

            state["text"] = wm_text
            state["pos"] = "11"
            state["mosaic"] = False
            user_watermark_state[user_id] = state
            user_modes[user_id] = "watermark_wait_style"

            await message.answer(
                "Выбери позицию водяного знака (сетку 3×3) и при необходимости включи Mosaic.",
                reply_markup=get_watermark_keyboard(pos="11", mosaic=False)
            )
            return

        # ===== ВОДЯНОЙ ЗНАК: напоминание =====
        if mode == "watermark_wait_style":
            await message.answer("Используй кнопки под прошлым сообщением для выбора позиции и Mosaic.")
            return

        # ===== MERGE: "Готово" =====
        if mode == "merge" and text_val in ("готово", "/done", "/merge"):
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
                logger.error(e)
                await message.answer("Ошибка при объединении.")
                return

            await message.answer_document(types.FSInputFile(merged_path), caption="Готово!")
            user_merge_files[user_id] = []
            return

        return

    @router.message(F.photo)
    async def handle_photo(message: types.Message, bot: Bot):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "doc_photo")

        photo = message.photo[-1]

        # проверка лимита по размеру
        if not await check_size_or_reject(message, photo.file_size):
            return

        await message.answer("Конвертирую фото в PDF...")

        file = await bot.get_file(photo.file_id)

        filename = f"photo_{user_id}_{photo.file_id}.jpg"
        src_path = FILES_DIR / filename
        await bot.download_file(file.file_path, destination=src_path)

        pdf_path = image_file_to_pdf(src_path)
        if not pdf_path:
            await message.answer("Не удалось конвертировать изображение.")
            return

        await message.answer_document(
            types.FSInputFile(pdf_path),
            caption="Готово."
        )
        
    # ================================
    #   CALLBACKS: WATERMARK UI
    # ================================
    @router.callback_query(F.data.startswith("wm_pos:"))
    async def wm_pos_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_watermark_state.setdefault(user_id, {})
        pos_code = callback.data.split(":", 1)[1]
        state["pos"] = pos_code
        user_watermark_state[user_id] = state

        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_watermark_keyboard(
                    pos=pos_code,
                    mosaic=state.get("mosaic", False)
                )
            )
        except Exception as e:
            logger.error(f"wm_pos edit_reply_markup error: {e}")

        await callback.answer()

    @router.callback_query(F.data == "wm_toggle_mosaic")
    async def wm_mosaic_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_watermark_state.setdefault(user_id, {})
        state["mosaic"] = not state.get("mosaic", False)

        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_watermark_keyboard(
                    pos=state.get("pos", "11"),
                    mosaic=state["mosaic"]
                )
            )
        except Exception as e:
            logger.error(f"wm_toggle_mosaic edit_reply_markup error: {e}")

        await callback.answer()

    @router.callback_query(F.data == "wm_apply")
    async def wm_apply_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_watermark_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        wm_text = state.get("text")
        pos = state.get("pos", "11")
        mosaic = state.get("mosaic", False)

        if not pdf_path or not Path(pdf_path).exists() or not wm_text:
            await callback.answer("Нет данных для водяного знака, начните заново.", show_alert=True)
            user_modes[user_id] = "watermark"
            user_watermark_state[user_id] = {}
            return

        await callback.answer()
        try:
            await callback.message.edit_text("Добавляю водяной знак в PDF...")
        except Exception:
            pass

        out_path = apply_watermark(Path(pdf_path), wm_text, pos, mosaic)

        if not out_path or not out_path.exists():
            await callback.message.answer("Не получилось сохранить PDF с водяным знаком.")
            return

        await callback.message.answer_document(
            types.FSInputFile(out_path),
            caption="Готово: PDF с водяным знаком."
        )

        user_watermark_state[user_id] = {}
        user_modes[user_id] = "compress"

    # ================================
    #   CALLBACKS: PAGES EDITOR
    # ================================
    @router.callback_query(F.data == "pages_action:rotate")
    async def pages_rotate_action(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not is_pro(user_id):
            await callback.answer("Только для PRO.", show_alert=True)
            return

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await callback.answer("Нет загруженного PDF. Сначала пришли файл в режиме редактора.", show_alert=True)
            return

        if num_pages == 1:
            # одна страница — сразу просим угол
            state["rotate_pages"] = [1]
            user_pages_state[user_id] = state
            user_modes[user_id] = "pages_rotate_wait_angle"

            await callback.message.answer(
                "В файле 1 страница.\n"
                "Выбери угол поворота:",
                reply_markup=get_rotate_keyboard()
            )
        else:
            # несколько страниц — сначала спрашиваем какие
            user_modes[user_id] = "pages_rotate_wait_pages"
            await callback.message.answer(
                f"Страниц в файле: {num_pages}.\n\n"
                "Какие страницы нужно повернуть?\n\n"
                "Примеры:\n"
                "• 2            — только 2 страницу\n"
                "• 1-3          — страницы 1,2,3\n"
                "• 1,3,5-7      — страницы 1,3,5,6,7\n"
                "• all          — все страницы"
            )

        await callback.answer()

    @router.callback_query(F.data == "pages_action:delete")
    async def pages_delete_action(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not is_pro(user_id):
            await callback.answer("Только для PRO.", show_alert=True)
            return

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await callback.answer("Нет загруженного PDF. Сначала пришли файл в режиме редактора.", show_alert=True)
            return

        user_modes[user_id] = "pages_delete_wait_pages"
        await callback.message.answer(
            f"Страниц в файле: {num_pages}.\n\n"
            "Какие страницы удалить?\n\n"
            "Примеры:\n"
            "• 2            — только 2 страницу\n"
            "• 1-3          — страницы 1,2,3\n"
            "• 1,3,5-7      — страницы 1,3,5,6,7"
        )
        await callback.answer()

    @router.callback_query(F.data == "pages_action:extract")
    async def pages_extract_action(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not is_pro(user_id):
            await callback.answer("Только для PRO.", show_alert=True)
            return

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await callback.answer("Нет загруженного PDF. Сначала пришли файл в режиме редактора.", show_alert=True)
            return

        user_modes[user_id] = "pages_extract_wait_pages"
        await callback.message.answer(
            f"Страниц в файле: {num_pages}.\n\n"
            "Какие страницы извлечь в новый PDF?\n\n"
            "Примеры:\n"
            "• 2            — только 2 страницу\n"
            "• 1-3          — страницы 1,2,3\n"
            "• 1,3,5-7      — страницы 1,3,5,6,7\n"
            "• all          — весь документ (копия)"
        )
        await callback.answer()

    @router.callback_query(F.data == "pages_action:cancel")
    async def pages_cancel_action(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        user_pages_state[user_id] = {}
        user_modes[user_id] = "compress"

        await callback.message.answer(
            "Редактирование страниц завершено.\n"
            "Можно выбрать другой режим или прислать PDF для сжатия."
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("pages_rotate_angle:"))
    async def pages_rotate_angle_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        data = callback.data.split(":", 1)[1]  # "+90" / "-90" / "180"
        try:
            angle = int(data)
        except ValueError:
            await callback.answer("Некорректный угол.", show_alert=True)
            return

        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not is_pro(user_id):
            await callback.answer("Только для PRO.", show_alert=True)
            return

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await callback.answer("Нет загруженного PDF.", show_alert=True)
            user_modes[user_id] = "compress"
            return

        rotate_pages = state.get("rotate_pages")
        if not rotate_pages:
            # если по какой-то причине страниц нет — считаем, что все
            rotate_pages = list(range(1, num_pages + 1))

        try:
            reader = PdfReader(str(pdf_path))
        except Exception as e:
            logger.error(f"Pages rotate open error: {e}")
            await callback.message.answer("Не удалось открыть PDF.")
            await callback.answer()
            return

        writer = PdfWriter()
        rotate_set = set(rotate_pages)
        for idx, page in enumerate(reader.pages, start=1):
            if idx in rotate_set:
                rotate_page_inplace(page, angle)
            writer.add_page(page)

        out_path = FILES_DIR / f"{Path(pdf_path).stem}_rotated.pdf"
        try:
            with open(out_path, "wb") as f:
                writer.write(f)
        except Exception as e:
            logger.error(f"Pages rotate write error: {e}")
            await callback.message.answer("Ошибка при сохранении PDF после поворота.")
            await callback.answer()
            return

        await callback.message.answer_document(
            types.FSInputFile(out_path),
            caption=f"Готово: страницы повёрнуты на {angle}°."
        )

        # обновляем стейт, очищаем rotate_pages
        state["pdf_path"] = out_path
        state["pages"] = num_pages
        state.pop("rotate_pages", None)
        user_pages_state[user_id] = state
        user_modes[user_id] = "pages_menu"

        await callback.message.answer(
            "Можно продолжить редактирование страниц.\n"
            "Выбери действие:",
            reply_markup=get_pages_menu_keyboard()
        )
        await callback.answer()

    @router.callback_query(F.data == "pages_back_to_menu")
    async def pages_back_to_menu_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            user_modes[user_id] = "compress"
            await callback.message.answer("Нет активного документа. Выбери режим и пришли PDF.")
        else:
            user_modes[user_id] = "pages_menu"
            await callback.message.answer(
                f"Редактор страниц PDF.\n"
                f"Страниц в документе: {num_pages}\n\n"
                "Выбери действие:",
                reply_markup=get_pages_menu_keyboard()
            )

        await callback.answer()

    # ================================
    #   START BOT
    # ================================
    dp.include_router(start_router) 
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
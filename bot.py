import asyncio
import subprocess
import zipfile
from io import BytesIO
import os
from pathlib import Path
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from aiogram import Bot, Dispatcher, types, F
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
)

# =========================
#   USER STATES
# =========================
# mode:
#   compress, pdf_text, doc_photo, merge, split, ocr, searchable_pdf,
#   watermark, watermark_wait_text, watermark_wait_style,
#   pages_wait_pdf, pages_menu,
#   pages_rotate_wait_pages, pages_rotate_wait_angle,
#   pages_delete_wait_pages, pages_extract_wait_pages
user_modes: dict[int, str] = {}

# list of files for merging
user_merge_files: dict[int, list[Path]] = {}

# состояние для водяных знаков: user_id -> {"pdf_path": Path, "text": str, "pos": "11", "mosaic": bool}
user_watermark_state: dict[int, dict] = {}

# состояние для редактора страниц: user_id -> {"pdf_path": Path, "pages": int, ...}
# доп. поля по ситуации:
#   "rotate_pages": list[int]
user_pages_state: dict[int, dict] = {}

# =========================
#   MAIN
# =========================
async def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set in environment")
        return

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    logger.info("Bot started")

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

    # ================================
    #   COMMAND: /start
    # ================================
    @dp.message(Command("start"))
    async def start_cmd(message: types.Message):
        user_id = message.from_user.id
        username = message.from_user.username

        user_modes[user_id] = "compress"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}

        tier = "PRO" if is_pro(user_id) else "FREE"
        limit_mb = format_mb(get_user_limit(user_id))

        logger.info(f"/start from {user_id} ({username}), tier={tier}")
        await message.answer(
            "👋 Привет! Я конвертирую и обрабатываю файлы в PDF.\n\n"
            "Выбери режим на клавиатуре и пришли файл:\n\n"
            "Основные инструменты:\n"
            "• 📉 Сжать PDF\n"
            "• 📎 Объединить PDF\n"
            "• ✂️ Разделить PDF\n"
            "• 📝 PDF → текст\n"
            "• 📄 Документ/фото → PDF\n\n"
            "PRO-инструменты:\n"
            "• 🔍 OCR\n"
            "• 📑 Searchable PDF\n"
            "• 🧩 Редактор страниц\n"
            "• 🛡 Водяной знак\n\n"
            f"Текущий тариф: <b>{tier}</b>\n"
            f"Лимит: <b>{limit_mb}</b>\n\n"
            "Подключить PRO-версию: /pro",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )

    # ================================
    #   COMMAND: /pro
    # ================================
    @dp.message(Command("pro"))
    async def pro_cmd(message: types.Message):
        user_id = message.from_user.id
        if is_pro(user_id):
            await message.answer(
                "✅ У вас уже PRO-доступ.\n"
                f"Текущий лимит: {format_mb(PRO_MAX_SIZE)}.\n\n"
                "Доступные PRO-функции:\n"
                "• OCR (сканы/фото → текст)\n"
                "• Searchable PDF (скан → PDF с выделяемым текстом)\n"
                "• Редактор страниц PDF (поворот/удаление/извлечение)\n"
                "• Водяные знаки для PDF\n"
                "• Файлы до 100 МБ",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "💼 <b>PRO-доступ</b>\n\n"
                "Что даёт сейчас:\n"
                "• Лимит до 100 МБ\n"
                "• OCR (сканы и фото → текст)\n"
                "• Searchable PDF (скан → PDF с выделяемым текстом)\n"
                "• Редактор страниц PDF (поворот/удаление/извлечение)\n"
                "• Водяные знаки для PDF\n"
                "• Приоритет в очереди (планируется)\n\n"
                "Чтобы подключить PRO — напишите владельцу бота.",
                parse_mode="HTML"
            )

    # ================================
    #   BUTTON MODES
    # ================================
    @dp.message(F.text == "📉 Сжать PDF")
    async def mode_compress(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "compress"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer("Режим: сжатие PDF. Пришли PDF.", reply_markup=get_main_keyboard())

    @dp.message(F.text == "📝 PDF → текст")
    async def mode_pdf_text(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "pdf_text"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer("Режим: PDF → текст. Пришли PDF.", reply_markup=get_main_keyboard())

    @dp.message(F.text == "📄 Документ/фото → PDF")
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

    @dp.message(F.text == "📎 Объединить PDF")
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

    @dp.message(F.text == "✂️ Разделить PDF")
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

    @dp.message(F.text == "🔍 OCR")
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

    @dp.message(F.text == "📑 Searchable PDF")
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

    @dp.message(F.text == "🧩 Редактор страниц")
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

    @dp.message(F.text == "🛡 Водяной знак")
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
    @dp.message(F.document & (F.document.mime_type == "application/pdf"))
    async def handle_pdf(message: types.Message):
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

            try:
                pdf_doc = fitz.open(str(src_path))
            except Exception as e:
                logger.error(f"OCR PDF open error: {e}")
                await message.answer("Не удалось открыть PDF для OCR.")
                return

            all_text_parts: list[str] = []

            try:
                for page_index, page in enumerate(pdf_doc, start=1):
                    pix = page.get_pixmap(dpi=300)
                    img_path = FILES_DIR / f"ocr_{user_id}_{page_index}.png"
                    pix.save(img_path)

                    text_page = pytesseract.image_to_string(
                        str(img_path),
                        lang="rus+eng"
                    )
                    all_text_parts.append(text_page)
            except Exception as e:
                logger.error(f"OCR processing error: {e}")
                await message.answer("Ошибка при распознавании текста.")
                return

            full_text = "\n\n".join(all_text_parts).strip()
            if not full_text:
                await message.answer("Не удалось распознать текст (возможно очень плохое качество скана).")
                return

            txt_path = FILES_DIR / (Path(doc_msg.file_name).stem + "_ocr.txt")
            txt_path.write_text(full_text, encoding="utf-8")

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

            try:
                pdf_doc = fitz.open(str(src_path))
            except Exception as e:
                logger.error(f"Searchable PDF open error: {e}")
                await message.answer("Не удалось открыть PDF.")
                return

            merger = PdfMerger()
            try:
                for page_index, page in enumerate(pdf_doc, start=1):
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    img = Image.open(BytesIO(img_bytes))

                    pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                        img,
                        extension="pdf",
                        lang="rus+eng"
                    )

                    merger.append(PdfReader(BytesIO(pdf_bytes)))

                out_path = FILES_DIR / (Path(doc_msg.file_name).stem + "_searchable.pdf")
                with open(out_path, "wb") as f:
                    merger.write(f)
                merger.close()
                pdf_doc.close()
            except Exception as e:
                logger.error(f"Searchable PDF error: {e}")
                await message.answer("Ошибка при создании searchable PDF.")
                return

            if not out_path.exists():
                await message.answer("Не удалось создать searchable PDF.")
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
        # MERGE MODE
        # =============================
        if mode == "merge":
            files_list = user_merge_files.setdefault(user_id, [])
            if len(files_list) >= 10:
                await message.answer("Максимум — 10 файлов.")
                return

            files_list.append(src_path)
            await message.answer(
                f"Добавлено. Сейчас файлов: {len(files_list)}.\n"
                "Когда закончишь — напиши «Готово»."
            )
            return

        # =============================
        # PDF → TEXT
        # =============================
        if mode == "pdf_text":
            await message.answer("Извлекаю текст...")
            text_chunks = []
            try:
                reader = PdfReader(str(src_path))
                for page in reader.pages:
                    txt = page.extract_text() or ""
                    text_chunks.append(txt)
            except Exception as e:
                logger.error(e)
                await message.answer("Не удалось извлечь текст.")
                return

            text_full = "\n\n".join(text_chunks).strip()
            if not text_full:
                await message.answer("Текста не найдено (возможно скан).")
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
            try:
                reader = PdfReader(str(src_path))
            except Exception as e:
                logger.error(e)
                await message.answer("Не удалось открыть PDF.")
                return

            n = len(reader.pages)
            if n <= 1:
                await message.answer("Там всего 1 страница.")
                return

            base = Path(doc_msg.file_name).stem
            pages = []

            try:
                for i in range(n):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])
                    out_path = FILES_DIR / f"{base}_page_{i+1}.pdf"
                    with open(out_path, "wb") as f:
                        writer.write(f)
                    pages.append(out_path)
            except Exception as e:
                logger.error(e)
                await message.answer("Ошибка при разделении.")
                return

            if n <= 10:
                for i, p in enumerate(pages, start=1):
                    await message.answer_document(
                        types.FSInputFile(p),
                        caption=f"Страница {i}/{n}"
                    )
            else:
                zip_path = FILES_DIR / f"{base}_pages.zip"
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

        gs_cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={compressed_path}",
            str(src_path)
        ]

        try:
            subprocess.run(gs_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except Exception as e:
            logger.error(e)
            await message.answer("Ошибка Ghostscript.")
            return

        if not compressed_path.exists():
            await message.answer("Не удалось сжать PDF.")
            return

        await message.answer_document(types.FSInputFile(compressed_path), caption="Готово.")
        return

    # ================================
    #   DOC / IMAGE → PDF
    # ================================
    @dp.message(F.document & (F.document.mime_type != "application/pdf"))
    async def handle_doc(message: types.Message):
        doc_msg = message.document
        filename = doc_msg.file_name or "file"
        ext = filename.split(".")[-1].lower()

        # size check
        if not await check_size_or_reject(message, doc_msg.file_size):
            return

        # IMAGE AS FILE
        if doc_msg.mime_type and doc_msg.mime_type.startswith("image/"):
            file = await bot.get_file(doc_msg.file_id)
            src_path = FILES_DIR / filename
            await bot.download_file(file.file_path, destination=src_path)

            pdf_path = FILES_DIR / (Path(filename).stem + ".pdf")
            try:
                img = Image.open(src_path).convert("RGB")
                img.save(pdf_path, "PDF")
            except Exception as e:
                logger.error(e)
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

        await message.answer("Конвертирую документ...")

        file = await bot.get_file(doc_msg.file_id)
        src_path = FILES_DIR / filename
        await bot.download_file(file.file_path, destination=src_path)

        lo_path = "soffice" if os.name != "nt" else r"C:\Program Files\LibreOffice\program\soffice.exe"
        logger.info(f"LibreOffice binary: {lo_path}")

        try:
            subprocess.run(
                [lo_path, "--headless", "--convert-to", "pdf", "--outdir", str(FILES_DIR), str(src_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except Exception as e:
            logger.error(e)
            await message.answer("Ошибка LibreOffice.")
            return

        pdf_path = FILES_DIR / (Path(filename).stem + ".pdf")
        if not pdf_path.exists():
            await message.answer("PDF не найден после конвертации.")
            return

        await message.answer_document(types.FSInputFile(pdf_path), caption="Готово.")
        return

    # ================================
    #   TEXT COMMANDS (PAGES + MERGE + WATERMARK)
    # ================================
    @dp.message(F.text)
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

    # ================================
    #   CALLBACKS: WATERMARK UI
    # ================================
    @dp.callback_query(F.data.startswith("wm_pos:"))
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

    @dp.callback_query(F.data == "wm_toggle_mosaic")
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

    @dp.callback_query(F.data == "wm_apply")
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
    @dp.callback_query(F.data == "pages_action:rotate")
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

    @dp.callback_query(F.data == "pages_action:delete")
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

    @dp.callback_query(F.data == "pages_action:extract")
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

    @dp.callback_query(F.data == "pages_action:cancel")
    async def pages_cancel_action(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        user_pages_state[user_id] = {}
        user_modes[user_id] = "compress"

        await callback.message.answer(
            "Редактирование страниц завершено.\n"
            "Можно выбрать другой режим или прислать PDF для сжатия."
        )
        await callback.answer()

    @dp.callback_query(F.data.startswith("pages_rotate_angle:"))
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

    @dp.callback_query(F.data == "pages_back_to_menu")
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
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import subprocess
from pathlib import Path
import os
import logging
import zipfile
import fitz  # PyMuPDF
import pytesseract

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from PyPDF2 import PdfReader, PdfMerger, PdfWriter

# =========================
#   LOAD ENV
# =========================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ===== PRO / FREE SETTINGS =====
PRO_USERS_RAW = os.getenv("PRO_USERS", "")  # comma-separated user IDs

PRO_USERS: set[int] = set()
for part in PRO_USERS_RAW.split(","):
    part = part.strip()
    if part.isdigit():
        PRO_USERS.add(int(part))

FREE_MAX_SIZE = 20 * 1024 * 1024      # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024      # 100 MB


def is_pro(user_id: int) -> bool:
    return user_id in PRO_USERS


def get_user_limit(user_id: int) -> int:
    return PRO_MAX_SIZE if is_pro(user_id) else FREE_MAX_SIZE


def format_mb(bytes_size: int) -> str:
    return f"{bytes_size / (1024 * 1024):.0f} МБ"


# =========================
#   LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# =========================
#   FILE STORAGE
# =========================
BASE_DIR = Path(__file__).parent
FILES_DIR = BASE_DIR / "files"
FILES_DIR.mkdir(exist_ok=True)

# =========================
#   USER STATES
# =========================
# mode: compress, pdf_text, doc_photo, merge, split, ocr, watermark_*
user_modes: dict[int, str] = {}

# list of files for merging
user_merge_files: dict[int, list[Path]] = {}

# состояние для водяных знаков: user_id -> {"pdf_path": Path, "text": str}
user_watermark_state: dict[int, dict] = {}


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

    # ===== Keyboard =====
    def get_main_keyboard() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📉 Сжать PDF"),
                    KeyboardButton(text="📎 Объединить PDF"),
                ],
                [
                    KeyboardButton(text="✂️ Разделить PDF"),
                    KeyboardButton(text="📝 PDF → текст"),
                ],
                [
                    KeyboardButton(text="📄 Документ/фото → PDF"),
                ],
                [
                    KeyboardButton(text="🔍 OCR (PRO)"),
                    KeyboardButton(text="🛡 Водяной знак (PRO)"),
                ],
            ],
            resize_keyboard=True
        )

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

        tier = "PRO" if is_pro(user_id) else "FREE"
        limit_mb = format_mb(get_user_limit(user_id))

        logger.info(f"/start from {user_id} ({username}), tier={tier}")
        await message.answer(
            "👋 Привет! Я конвертирую и обрабатываю файлы в PDF.\n\n"
            "Выбери режим на клавиатуре и пришли файл:\n"
            "• 📉 Сжать PDF\n"
            "• 📎 Объединить PDF\n"
            "• ✂️ Разделить PDF\n"
            "• 📝 PDF → текст\n"
            "• 📄 Документ/фото → PDF\n"
            "• 🔍 OCR (PRO)\n"
            "• 🛡 Водяной знак (PRO)\n\n"
            f"Текущий тариф: <b>{tier}</b>\n"
            f"Макс размер файла: <b>{limit_mb}</b>\n\n"
            "По умолчанию: сжатие PDF.\n"
            "Команда /pro — как получить PRO.",
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
                "• Водяные знаки для PDF\n"
                "• Приоритет в очереди\n\n"
                "В будущем в PRO появятся:\n"
                "• Расширенное редактирование PDF\n\n"
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
        await message.answer("Режим: сжатие PDF. Пришли PDF.", reply_markup=get_main_keyboard())

    @dp.message(F.text == "📝 PDF → текст")
    async def mode_pdf_text(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "pdf_text"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        await message.answer("Режим: PDF → текст. Пришли PDF.", reply_markup=get_main_keyboard())

    @dp.message(F.text == "📄 Документ/фото → PDF")
    async def mode_doc_photo(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "doc_photo"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
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
        await message.answer(
            "Режим: разделение PDF.\nПришли один PDF.",
            reply_markup=get_main_keyboard()
        )

    @dp.message(F.text == "🔍 OCR (PRO)")
    async def mode_ocr(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "ocr"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
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

    @dp.message(F.text == "🛡 Водяной знак (PRO)")
    async def mode_watermark(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "watermark"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}

        if not is_pro(user_id):
            await message.answer(
                "Режим: 🛡 водяной знак для PDF.\n"
                "Функция доступна только для PRO-пользователей.\n\n"
                "Подробнее: /pro"
            )
        else:
            await message.answer(
                "Режим: 🛡 водяной знак.\n"
                "1) Пришли PDF-файл.\n"
                "2) Потом введи текст водяного знака.\n"
                "3) Выбери стиль (диагональ, центр, низ страницы)."
            )

    # ================================
    #   HANDLE PDF
    # ================================
    @dp.message(F.document & (F.document.mime_type == "application/pdf"))
    async def handle_pdf(message: types.Message):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "compress")
        doc = message.document

        # size check
        if not await check_size_or_reject(message, doc.file_size):
            return

        file = await bot.get_file(doc.file_id)
        src_path = FILES_DIR / doc.file_name
        await bot.download_file(file.file_path, destination=src_path)

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
                from PIL import Image
                for page_index, page in enumerate(pdf_doc, start=1):
                    pix = page.get_pixmap(dpi=300)
                    img_path = FILES_DIR / f"ocr_{user_id}_{page_index}.png"
                    pix.save(img_path)

                    img = Image.open(img_path)
                    text_page = pytesseract.image_to_string(
                        img,
                        lang="rus+eng"
                    )
                    all_text_parts.append(text_page)
                pdf_doc.close()
            except Exception as e:
                logger.error(f"OCR processing error: {e}")
                await message.answer("Ошибка при распознавании текста.")
                return

            full_text = "\n\n".join(all_text_parts).strip()
            if not full_text:
                await message.answer("Не удалось распознать текст (возможно очень плохое качество скана).")
                return

            txt_path = FILES_DIR / (Path(doc.file_name).stem + "_ocr.txt")
            txt_path.write_text(full_text, encoding="utf-8")

            await message.answer_document(
                types.FSInputFile(txt_path),
                caption="Готово: OCR-текст из PDF."
            )
            logger.info(f"OCR PDF done for user {user_id}")
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
                "Например: CONFIDENTIAL, DRAFT, КОПИЯ.\n"
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

            txt_path = FILES_DIR / (Path(doc.file_name).stem + ".txt")
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

            base = Path(doc.file_name).stem
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
        compressed_path = FILES_DIR / f"compressed_{doc.file_name}"

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
        doc = message.document
        filename = doc.file_name or "file"
        ext = filename.split(".")[-1].lower()

        # size check
        if not await check_size_or_reject(message, doc.file_size):
            return

        # IMAGE AS FILE
        if doc.mime_type and doc.mime_type.startswith("image/"):
            from PIL import Image
            file = await bot.get_file(doc.file_id)
            src_path = FILES_DIR / filename
            await bot.download_file(file.file_path, destination=src_path)

            # если режим OCR и PRO — делаем OCR по изображению
            user_id = message.from_user.id
            mode = user_modes.get(user_id, "compress")

            if mode == "ocr":
                if not is_pro(user_id):
                    await message.answer("OCR доступен только для PRO-пользователей. См. /pro")
                    return

                await message.answer("Распознаю текст на изображении (OCR)...")
                try:
                    img = Image.open(src_path)
                    text_page = pytesseract.image_to_string(img, lang="rus+eng")
                except Exception as e:
                    logger.error(f"OCR image-doc error: {e}")
                    await message.answer("Ошибка при распознавании текста.")
                    return

                full_text = (text_page or "").strip()
                if not full_text:
                    await message.answer("Не удалось распознать текст на изображении.")
                    return

                txt_path = FILES_DIR / (Path(filename).stem + "_ocr.txt")
                txt_path.write_text(full_text, encoding="utf-8")

                await message.answer_document(
                    types.FSInputFile(txt_path),
                    caption="Готово: OCR-текст из изображения."
                )
                logger.info(f"OCR IMAGE-DOC done for user {user_id}")
                return

            # иначе — конвертация в PDF
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

        file = await bot.get_file(doc.file_id)
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
    #   PHOTO (telegram photo) → OCR / PDF
    # ================================
    @dp.message(F.photo)
    async def handle_photo(message: types.Message):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "compress")

        photo = message.photo[-1]  # самое большое
        # size check
        if not await check_size_or_reject(message, photo.file_size):
            return

        file = await bot.get_file(photo.file_id)
        jpg_name = f"{photo.file_id}.jpg"
        src_path = FILES_DIR / jpg_name
        await bot.download_file(file.file_path, destination=src_path)

        from PIL import Image

        # OCR режим
        if mode == "ocr":
            if not is_pro(user_id):
                await message.answer("OCR доступен только для PRO-пользователей. См. /pro")
                return

            await message.answer("Распознаю текст на фото (OCR)...")
            try:
                img = Image.open(src_path)
                text_page = pytesseract.image_to_string(img, lang="rus+eng")
            except Exception as e:
                logger.error(f"OCR photo error: {e}")
                await message.answer("Ошибка при распознавании текста.")
                return

            full_text = (text_page or "").strip()
            if not full_text:
                await message.answer("Не удалось распознать текст на фото.")
                return

            txt_path = FILES_DIR / f"{photo.file_id}_ocr.txt"
            txt_path.write_text(full_text, encoding="utf-8")

            await message.answer_document(
                types.FSInputFile(txt_path),
                caption="Готово: OCR-текст с фото."
            )
            logger.info(f"OCR PHOTO done for user {user_id}")
            return

        # Остальные режимы: просто фото → PDF
        pdf_path = FILES_DIR / (Path(jpg_name).stem + ".pdf")
        try:
            img = Image.open(src_path).convert("RGB")
            img.save(pdf_path, "PDF")
        except Exception as e:
            logger.error(f"PHOTO->PDF error: {e}")
            await message.answer("Не удалось конвертировать фото в PDF.")
            return

        await message.answer_document(
            types.FSInputFile(pdf_path),
            caption="Фото сконвертировано в PDF."
        )
        logger.info(f"PHOTO converted to PDF for user {user_id}")
        return

    # ================================
    #   TEXT COMMANDS (MERGE + WATERMARK)
    # ================================
    @dp.message(F.text)
    async def handle_text(message: types.Message):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "compress")
        text = (message.text or "").strip().lower()

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
            user_watermark_state[user_id] = state
            user_modes[user_id] = "watermark_wait_style"

            await message.answer(
                "Теперь выбери стиль водяного знака:\n"
                "1 — Диагональ по центру (крупный серый текст)\n"
                "2 — По центру страницы\n"
                "3 — Внизу страницы\n\n"
                "Отправь цифру: 1, 2 или 3."
            )
            return

        # ===== ВОДЯНОЙ ЗНАК: шаг 3 — стиль и генерация =====
        if mode == "watermark_wait_style":
            state = user_watermark_state.get(user_id) or {}
            pdf_path = state.get("pdf_path")
            wm_text = state.get("text")

            if not pdf_path or not Path(pdf_path).exists() or not wm_text:
                await message.answer("Что-то пошло не так. Начни добавление водяного знака заново.")
                user_modes[user_id] = "watermark"
                user_watermark_state[user_id] = {}
                return

            choice = (message.text or "").strip()
            if choice not in ("1", "2", "3"):
                await message.answer("Нужно отправить цифру: 1, 2 или 3.")
                return

            style = int(choice)

            await message.answer("Добавляю водяной знак в PDF...")

            pdf_in = Path(pdf_path)
            pdf_out = FILES_DIR / f"{pdf_in.stem}_watermark.pdf"

            try:
                doc = fitz.open(str(pdf_in))
            except Exception as e:
                logger.error(f"Watermark open error: {e}")
                await message.answer("Не удалось открыть PDF для водяного знака.")
                return

            try:
                for page in doc:
                    rect = page.rect
                    w = rect.width
                    h = rect.height

                    fontsize = max(w, h) / 20
                    color = (0.7, 0.7, 0.7)

                    if style == 1:
                        # диагональ по центру
                        point = fitz.Point(w / 2, h / 2)
                        page.insert_text(
                            point,
                            wm_text,
                            fontsize=fontsize,
                            color=color,
                            rotate=45,
                        )

                    elif style == 2:
                        # по центру
                        point = fitz.Point(w / 2, h / 2)
                        page.insert_text(
                            point,
                            wm_text,
                            fontsize=fontsize * 0.7,
                            color=color,
                        )

                    elif style == 3:
                        # внизу страницы
                        point = fitz.Point(w / 2, h - 40)
                        page.insert_text(
                            point,
                            wm_text,
                            fontsize=fontsize * 0.6,
                            color=color,
                        )

                doc.save(str(pdf_out))
                doc.close()

            except Exception as e:
                logger.error(f"Watermark apply error: {e}")
                await message.answer("Ошибка при добавлении водяного знака.")
                return

            if not pdf_out.exists():
                await message.answer("Не получилось сохранить PDF с водяным знаком.")
                return

            await message.answer_document(
                types.FSInputFile(pdf_out),
                caption="Готово: PDF с водяным знаком."
            )

            user_watermark_state[user_id] = {}
            user_modes[user_id] = "compress"
            return

        # ===== MERGE: "Готово" =====
        if mode == "merge" and text in ("готово", "/done", "/merge"):
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
    #   START BOT
    # ================================
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
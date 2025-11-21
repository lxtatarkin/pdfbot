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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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

# состояние для водяных знаков: user_id -> {"pdf_path": Path, "text": str, "pos": "11", "mosaic": bool}
user_watermark_state: dict[int, dict] = {}


# =========================
#   WATERMARK HELPERS
# =========================
def get_watermark_keyboard(pos: str | None = None, mosaic: bool = False) -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура 3×3 для выбора позиции + чекбокс Mosaic + кнопка OK.
    pos — строка вида "rc" (row, col), где r,c в [0..2].
    """
    grid: list[list[InlineKeyboardButton]] = []

    for r in range(3):
        row: list[InlineKeyboardButton] = []
        for c in range(3):
            code = f"{r}{c}"
            text = "●" if pos == code else " "
            row.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"wm_pos:{code}"
                )
            )
        grid.append(row)

    mosaic_text = "✅ Mosaic" if mosaic else "Mosaic"
    grid.append([
        InlineKeyboardButton(text=mosaic_text, callback_data="wm_toggle_mosaic")
    ])
    grid.append([
        InlineKeyboardButton(text="OK", callback_data="wm_apply")
    ])

    return InlineKeyboardMarkup(inline_keyboard=grid)


def apply_watermark(pdf_in: Path, wm_text: str, pos: str, mosaic: bool) -> Path | None:
    """
    Нанесение водяного знака на PDF.
    pos — "rc" (r,c = 0..2) позиция в сетке 3×3, если mosaic = False.
    Если mosaic = True — делаем простую "заплатку" текста по всей странице.
    """
    pdf_out = FILES_DIR / f"{pdf_in.stem}_watermark.pdf"

    try:
        doc = fitz.open(str(pdf_in))
    except Exception as e:
        logger.error(f"Watermark open error: {e}")
        return None

    try:
        for page in doc:
            rect = page.rect
            w, h = rect.width, rect.height

            fontsize = max(w, h) / 25
            color = (0.7, 0.7, 0.7)

            if mosaic:
                # простая "мозаика": сетка 4×4 по всей странице
                rows = 4
                cols = 4
                step_x = w / cols
                step_y = h / rows
                for i in range(rows):
                    for j in range(cols):
                        x = (j + 0.5) * step_x
                        y = (i + 0.5) * step_y
                        point = fitz.Point(x, y)
                        page.insert_text(
                            point,
                            wm_text,
                            fontsize=fontsize * 0.7,
                            color=color,
                        )
            else:
                # одиночный watermark по сетке 3×3
                try:
                    row = int(pos[0])
                    col = int(pos[1])
                except Exception:
                    row, col = 1, 1  # по центру по умолчанию

                # координаты центров ячеек 3×3
                xs = [w * 0.17, w * 0.5, w * 0.83]
                ys = [h * 0.2, h * 0.5, h * 0.8]

                x = xs[min(max(col, 0), 2)]
                y = ys[min(max(row, 0), 2)]

                point = fitz.Point(x, y)

                page.insert_text(
                    point,
                    wm_text,
                    fontsize=fontsize,
                    color=color,
                )

        doc.save(str(pdf_out))
        doc.close()
    except Exception as e:
        logger.error(f"Watermark apply error: {e}")
        return None

    return pdf_out


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
            from PIL import Image
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
    #   TEXT COMMANDS (MERGE + WATERMARK)
    # ================================
    @dp.message(F.text)
    async def handle_text(message: types.Message):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "compress")
        text_val = (message.text or "").strip().lower()

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
            # по умолчанию центр "11"
            state["pos"] = "11"
            state["mosaic"] = False
            user_watermark_state[user_id] = state
            user_modes[user_id] = "watermark_wait_style"

            await message.answer(
                "Выбери позицию водяного знака (сетку 3×3) и при необходимости включи Mosaic.",
                reply_markup=get_watermark_keyboard(pos="11", mosaic=False)
            )
            return

        # ===== ВОДЯНОЙ ЗНАК: шаг 3 — выбор стиля уже идёт через inline-кнопки =====
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
    #   START BOT
    # ================================
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
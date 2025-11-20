import asyncio
import subprocess
from pathlib import Path
import os
import logging
import zipfile

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from PyPDF2 import PdfReader, PdfMerger, PdfWriter  # PDF: текст, merge, split

# грузим .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ===== PRO / FREE настройки =====
PRO_USERS_RAW = os.getenv("PRO_USERS", "")

# Множество PRO-пользователей (ID телеграма)
PRO_USERS: set[int] = set()
for part in PRO_USERS_RAW.split(","):
    part = part.strip()
    if part.isdigit():
        PRO_USERS.add(int(part))

# Лимиты по размеру файлов (в байтах)
FREE_MAX_SIZE = 20 * 1024 * 1024      # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024      # 100 MB


def is_pro(user_id: int) -> bool:
    return user_id in PRO_USERS


def get_user_limit(user_id: int) -> int:
    return PRO_MAX_SIZE if is_pro(user_id) else FREE_MAX_SIZE


def format_mb(bytes_size: int) -> str:
    return f"{bytes_size / (1024 * 1024):.0f} МБ"


# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

# Папка для файлов
BASE_DIR = Path(__file__).parent
FILES_DIR = BASE_DIR / "files"
FILES_DIR.mkdir(exist_ok=True)

# Режимы пользователя: user_id -> mode ("compress", "pdf_text", "doc_photo", "merge", "split")
user_modes: dict[int, str] = {}

# Для режима объединения: user_id -> список путей к PDF
user_merge_files: dict[int, list[Path]] = {}


async def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set in environment")
        return

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    logger.info("Bot started")

    # ===== общая проверка размера файла =====
    async def check_size_or_reject(message: types.Message, size_bytes: int | None) -> bool:
        """
        Возвращает True, если файл можно обрабатывать.
        Если превышен лимит тарифа — отправляет сообщение и возвращает False.
        """
        user_id = message.from_user.id
        max_size = get_user_limit(user_id)
        tier = "PRO" if is_pro(user_id) else "FREE"

        if size_bytes is not None and size_bytes > max_size:
            limit_str = format_mb(max_size)
            await message.answer(
                f"Файл слишком большой для вашего тарифа ({tier}).\n"
                f"Текущий лимит: {limit_str}.\n\n"
                "Для работы с более крупными файлами нужен PRO-доступ.\n"
                "Посмотрите /pro для деталей."
            )
            logger.info(
                f"User {user_id} exceeded size limit: size={size_bytes}, "
                f"limit={max_size}, tier={tier}"
            )
            return False

        return True

    # ===== КЛАВИАТУРА РЕЖИМОВ =====
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
            ],
            resize_keyboard=True
        )

    @dp.message(Command("start"))
    async def start_cmd(message: types.Message):
        user_id = message.from_user.id
        username = message.from_user.username
        user_modes[user_id] = "compress"
        user_merge_files[user_id] = []

        tier = "PRO" if is_pro(user_id) else "FREE"
        limit_mb = format_mb(get_user_limit(user_id))

        logger.info(f"/start from {user_id} ({username}), tier={tier}")
        text = (
            "👋 Привет! Я конвертирую и обрабатываю файлы в PDF прямо в Telegram.\n\n"
            "Выбери режим на клавиатуре ниже и пришли файл(ы):\n"
            "• 📉 Сжать PDF — уменьшить размер PDF\n"
            "• 📎 Объединить PDF — склеить несколько PDF в один\n"
            "• ✂️ Разделить PDF — разбить PDF на отдельные страницы\n"
            "• 📝 PDF → текст — вытащить текст из PDF в .txt\n"
            "• 📄 Документ/фото → PDF — сделать PDF из DOC/XLS/PPT или картинки\n\n"
            f"Текущий тариф: <b>{tier}</b>\n"
            f"Максимальный размер файла: <b>{limit_mb}</b>\n\n"
            "По умолчанию: сжатие PDF.\n"
            "Команда /pro — как получить PRO."
        )
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

    # ===== /pro =====

    @dp.message(Command("pro"))
    async def pro_cmd(message: types.Message):
        user_id = message.from_user.id

        if is_pro(user_id):
            limit_str = format_mb(get_user_limit(user_id))
            await message.answer(
                "✅ У вас уже активен <b>PRO</b>-доступ.\n\n"
                f"Текущий лимит файла: <b>{limit_str}</b>.\n"
                "Спасибо за поддержку!",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "💼 <b>PRO-версия бота</b>\n\n"
                "Что даёт PRO сейчас:\n"
                "• Лимит размера файла: до 100 МБ (вместо 20 МБ)\n"
                "• Приоритет обработки\n\n"
                "В будущем в PRO появятся:\n"
                "• OCR (распознавание сканов)\n"
                "• водяные знаки и другие функции\n\n"
                "Сейчас PRO подключается вручную.\n"
                "Напишите владельцу бота, чтобы получить подробности.",
                parse_mode="HTML"
            )

    # ===== ОБРАБОТКА ВЫБОРА РЕЖИМА КНОПКАМИ =====

    @dp.message(F.text == "📉 Сжать PDF")
    async def set_mode_compress(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "compress"
        user_merge_files[user_id] = []
        await message.answer(
            "Режим: 📉 сжатие PDF. Пришли PDF-файл.",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Mode for {user_id} = compress")

    @dp.message(F.text == "📝 PDF → текст")
    async def set_mode_pdf_text(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "pdf_text"
        user_merge_files[user_id] = []
        await message.answer(
            "Режим: 📝 PDF → текст. Пришли PDF-файл.",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Mode for {user_id} = pdf_text")

    @dp.message(F.text == "📄 Документ/фото → PDF")
    async def set_mode_doc_photo(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "doc_photo"
        user_merge_files[user_id] = []
        await message.answer(
            "Режим: 📄 документ/фото → PDF.\n"
            "Пришли офисный документ (DOCX, XLSX, PPTX) или картинку (как фото или как файл).",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Mode for {user_id} = doc_photo")

    @dp.message(F.text == "📎 Объединить PDF")
    async def set_mode_merge(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "merge"
        user_merge_files[user_id] = []
        await message.answer(
            "Режим: 📎 объединение PDF.\n"
            "1️⃣ Пришли 2–10 PDF-файлов подряд.\n"
            "2️⃣ Когда закончишь — напиши текстом «Готово».\n\n"
            "Я склею их в один PDF в порядке отправки.",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Mode for {user_id} = merge")

    @dp.message(F.text == "✂️ Разделить PDF")
    async def set_mode_split(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "split"
        user_merge_files[user_id] = []
        await message.answer(
            "Режим: ✂️ разделить PDF.\n"
            "Пришли один PDF-файл, я разобью его по страницам.\n"
            "Если страниц ≤ 10 — отправлю отдельные PDF для каждой страницы.\n"
            "Если страниц больше — пришлю ZIP-архив.",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Mode for {user_id} = split")

    # ===== PDF: в зависимости от режима =====

    @dp.message(F.document & (F.document.mime_type == "application/pdf"))
    async def handle_pdf(message: types.Message):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "compress")
        doc = message.document

        # проверка лимита размера
        if not await check_size_or_reject(message, doc.file_size):
            return

        logger.info(f"PDF from {user_id}, mode={mode}")

        file = await bot.get_file(doc.file_id)
        src_path = FILES_DIR / doc.file_name
        await bot.download_file(file.file_path, destination=src_path)

        # --- РЕЖИМ: ОБЪЕДИНЕНИЕ PDF ---
        if mode == "merge":
            files_list = user_merge_files.setdefault(user_id, [])
            if len(files_list) >= 10:
                await message.answer("Можно добавить максимум 10 файлов для объединения.")
                return

            files_list.append(src_path)
            await message.answer(
                f"Файл добавлен для объединения. Сейчас в списке: {len(files_list)}.\n"
                "Когда добавишь все нужные — напиши «Готово»."
            )
            logger.info(f"User {user_id} added PDF to merge list: {src_path}")
            return

        # --- РЕЖИМ: PDF -> текст ---
        if mode == "pdf_text":
            await message.answer("Извлекаю текст из PDF...")
            text_chunks: list[str] = []

            try:
                reader = PdfReader(str(src_path))
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text_chunks.append(page_text)
            except Exception as e:
                logger.error(f"PDF->TEXT error: {e}")
                await message.answer("Не удалось извлечь текст из PDF.")
                return

            full_text = "\n\n".join(text_chunks).strip()

            if not full_text:
                await message.answer(
                    "В этом PDF не удалось найти текст (возможно, это скан без распознавания)."
                )
                return

            txt_name = Path(doc.file_name).with_suffix(".txt").name
            txt_path = FILES_DIR / txt_name
            txt_path.write_text(full_text, encoding="utf-8")

            await message.answer_document(
                types.FSInputFile(txt_path),
                caption="Готово: текст из PDF."
            )
            logger.info("PDF text extracted and sent")
            return

        # --- РЕЖИМ: РАЗДЕЛИТЬ PDF ПО СТРАНИЦАМ ---
        if mode == "split":
            await message.answer("Разделяю PDF по страницам...")

            try:
                reader = PdfReader(str(src_path))
                num_pages = len(reader.pages)
            except Exception as e:
                logger.error(f"PDF split read error: {e}")
                await message.answer("Не удалось прочитать PDF для разделения.")
                return

            if num_pages <= 1:
                await message.answer("В этом PDF только одна страница, разделять нечего.")
                return

            base_name = Path(doc.file_name).stem
            page_files: list[Path] = []

            try:
                for i in range(num_pages):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])

                    single_name = f"{base_name}_page_{i+1}.pdf"
                    single_path = FILES_DIR / single_name
                    with open(single_path, "wb") as f:
                        writer.write(f)

                    page_files.append(single_path)
            except Exception as e:
                logger.error(f"PDF split write error: {e}")
                await message.answer("Произошла ошибка при разделении PDF на страницы.")
                return

            # Если страниц немного — отправляем отдельными файлами
            if num_pages <= 10:
                for i, p in enumerate(page_files, start=1):
                    await message.answer_document(
                        types.FSInputFile(p),
                        caption=f"Страница {i} из {num_pages}"
                    )
                logger.info(f"PDF split into {num_pages} pages (sent separately) for user {user_id}")
            else:
                # Если страниц много — упакуем в ZIP
                zip_name = f"{base_name}_pages.zip"
                zip_path = FILES_DIR / zip_name

                try:
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                        for p in page_files:
                            zf.write(p, arcname=p.name)
                except Exception as e:
                    logger.error(f"ZIP create error for split PDF: {e}")
                    await message.answer("Не удалось упаковать страницы в ZIP.")
                    return

                await message.answer_document(
                    types.FSInputFile(zip_path),
                    caption=f"Готово: PDF разделён на {num_pages} страниц, отправляю ZIP-архив."
                )
                logger.info(f"PDF split into {num_pages} pages (zip) for user {user_id}")

            return

        # --- РЕЖИМ ПО УМОЛЧАНИЮ: сжатие PDF (Ghostscript) ---
        await message.answer("Сжимаю PDF... (глубокое сжатие)")
        compressed_path = FILES_DIR / f"compressed_{doc.file_name}"

        gs_cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",   # /screen /ebook /printer /prepress
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={compressed_path}",
            str(src_path)
        ]

        try:
            result = subprocess.run(
                gs_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except Exception as e:
            logger.error(f"Ghostscript subprocess error: {e}")
            await message.answer("Ошибка Ghostscript при сжатии PDF.")
            return

        if result.returncode != 0:
            logger.error(
                f"Ghostscript error, code={result.returncode}, stderr={result.stderr}"
            )
            await message.answer("Не удалось сжать PDF (ошибка Ghostscript).")
            return

        if not compressed_path.exists():
            logger.error("Ghostscript did not create compressed file")
            await message.answer("Не удалось сжать PDF.")
            return

        await message.answer_document(
            types.FSInputFile(compressed_path),
            caption="Готово: PDF-файл глубоко сжат."
        )
        logger.info("PDF deeply compressed with Ghostscript")

    # ===== ДОКУМЕНТЫ (не PDF): офис + изображения как файл =====

    @dp.message(F.document & (F.document.mime_type != "application/pdf"))
    async def handle_document(message: types.Message):
        doc = message.document
        filename = doc.file_name or "file"
        ext = filename.split(".")[-1].lower()
        logger.info(f"DOC ({ext}) from {message.from_user.id}, mime={doc.mime_type}")

        # проверка лимита размера
        if not await check_size_or_reject(message, doc.file_size):
            return

        # 1) Изображение, отправленное как файл
        if doc.mime_type and doc.mime_type.startswith("image/"):
            from PIL import Image

            file = await bot.get_file(doc.file_id)
            src_path = FILES_DIR / filename
            await bot.download_file(file.file_path, destination=src_path)

            pdf_name = Path(filename).with_suffix(".pdf")
            pdf_path = FILES_DIR / pdf_name

            try:
                image = Image.open(src_path).convert("RGB")
                image.save(pdf_path, "PDF")
            except Exception as e:
                logger.error(f"Image->PDF convert error: {e}")
                await message.answer("Не удалось конвертировать изображение в PDF.")
                return

            await message.answer_document(
                types.FSInputFile(pdf_path),
                caption="Изображение сконвертировано в PDF."
            )
            logger.info("IMAGE-DOC converted to PDF")
            return

        # 2) Офисные документы
        supported = {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}

        if ext not in supported:
            await message.answer(
                "Документ сохранён.\n"
                "Пока я умею конвертировать в PDF:\n"
                "• DOC, DOCX, XLS, XLSX, PPT, PPTX\n"
                "• изображения, отправленные как файл."
            )
            return

        file = await bot.get_file(doc.file_id)
        src_path = FILES_DIR / filename
        await bot.download_file(file.file_path, destination=src_path)

        await message.answer("Конвертирую документ в PDF, подождите несколько секунд...")

        if os.name == "nt":
            lo_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
        else:
            lo_path = "soffice"

        logger.info(f"Using LibreOffice binary: {lo_path} (os.name={os.name})")

        try:
            result = subprocess.run(
                [
                    lo_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(FILES_DIR),
                    str(src_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            logger.error(f"LibreOffice subprocess error: {e}")
            await message.answer("Произошла ошибка при конвертации документа (subprocess).")
            return

        if result.returncode != 0:
            logger.error(
                f"LibreOffice convert error, code={result.returncode}, stderr={result.stderr}"
            )
            await message.answer("Произошла ошибка при конвертации документа.")
            return

        pdf_name = Path(filename).with_suffix(".pdf").name
        pdf_path = FILES_DIR / pdf_name

        if not pdf_path.exists():
            logger.error(f"PDF file not found after conversion: {pdf_path}")
            await message.answer("PDF-файл не найден после конвертации.")
            return

        await message.answer_document(
            types.FSInputFile(pdf_path),
            caption="Готово: документ сконвертирован в PDF."
        )
        logger.info("DOC converted to PDF")

    # ===== ФОТО (как обычное фото) → PDF =====

    @dp.message(F.photo)
    async def handle_photo(message: types.Message):
        logger.info(f"PHOTO from {message.from_user.id}")
        from PIL import Image

        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)

        original_name = f"photo_{photo.file_id}.jpg"

        jpg_path = FILES_DIR / original_name
        await bot.download_file(file.file_path, destination=jpg_path)

        pdf_name = Path(original_name).with_suffix(".pdf")
        pdf_path = FILES_DIR / pdf_name

        image = Image.open(jpg_path).convert("RGB")
        image.save(pdf_path, "PDF")

        await message.answer_document(
            types.FSInputFile(pdf_path),
            caption="Фото сконвертировано в PDF."
        )
        logger.info("PHOTO converted to PDF")

    # ===== ТЕКСТ "Готово" ДЛЯ ЗАПУСКА ОБЪЕДИНЕНИЯ PDF =====

    @dp.message(F.text)
    async def handle_text_generic(message: types.Message):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "compress")
        text = (message.text or "").strip().lower()

        # Запускаем объединение только в режиме merge
        if mode == "merge" and text in ("готово", "/done", "/merge"):
            files_list = user_merge_files.get(user_id, [])
            if not files_list or len(files_list) < 2:
                await message.answer("Нужно минимум 2 PDF-файла для объединения.")
                return

            await message.answer(
                f"Объединяю {len(files_list)} PDF-файлов в один..."
            )

            first_name = Path(files_list[0]).stem
            merged_name = f"{first_name}_merged.pdf"
            merged_path = FILES_DIR / merged_name

            try:
                merger = PdfMerger()
                for p in files_list:
                    merger.append(str(p))
                merger.write(str(merged_path))
                merger.close()
            except Exception as e:
                logger.error(f"PDF merge error: {e}")
                await message.answer("Произошла ошибка при объединении PDF.")
                return

            await message.answer_document(
                types.FSInputFile(merged_path),
                caption=f"Готово: объединённый PDF ({len(files_list)} файлов)."
            )

            logger.info(f"User {user_id} got merged PDF: {merged_path}")
            user_merge_files[user_id] = []
            return

        # прочий текст — игнорируем
        return

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import subprocess
from pathlib import Path
import os
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from PyPDF2 import PdfReader  # для PDF -> текст

# грузим .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

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

# Режимы пользователя: user_id -> mode ("compress", "pdf_text", "doc_photo")
user_modes: dict[int, str] = {}


async def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set in environment")
        return

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    logger.info("Bot started")

    # ===== КЛАВИАТУРА РЕЖИМОВ =====
    def get_main_keyboard() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📉 Сжать PDF")],
                [KeyboardButton(text="📝 PDF → текст")],
                [KeyboardButton(text="📄 Документ/фото → PDF")],
            ],
            resize_keyboard=True
        )

    @dp.message(Command("start"))
    async def start_cmd(message: types.Message):
        logger.info(f"/start from {message.from_user.id} ({message.from_user.username})")
        text = (
            "👋 Привет! Я конвертирую файлы в PDF прямо в Telegram.\n\n"
            "Выбери режим на клавиатуре ниже и пришли файл:\n"
            "• 📉 Сжать PDF — уменьшить размер PDF\n"
            "• 📝 PDF → текст — вытащить текст из PDF в .txt\n"
            "• 📄 Документ/фото → PDF — сделать PDF из DOC/XLS/PPT или картинки\n\n"
            "По умолчанию: сжатие PDF."
        )
        # режим по умолчанию
        user_modes[message.from_user.id] = "compress"
        await message.answer(text, reply_markup=get_main_keyboard())

    # ===== ОБРАБОТКА ВЫБОРА РЕЖИМА КНОПКАМИ =====

    @dp.message(F.text == "📉 Сжать PDF")
    async def set_mode_compress(message: types.Message):
        user_modes[message.from_user.id] = "compress"
        await message.answer("Режим: 📉 сжатие PDF. Пришли PDF-файл.", reply_markup=get_main_keyboard())
        logger.info(f"Mode for {message.from_user.id} = compress")

    @dp.message(F.text == "📝 PDF → текст")
    async def set_mode_pdf_text(message: types.Message):
        user_modes[message.from_user.id] = "pdf_text"
        await message.answer("Режим: 📝 PDF → текст. Пришли PDF-файл.", reply_markup=get_main_keyboard())
        logger.info(f"Mode for {message.from_user.id} = pdf_text")

    @dp.message(F.text == "📄 Документ/фото → PDF")
    async def set_mode_doc_photo(message: types.Message):
        user_modes[message.from_user.id] = "doc_photo"
        await message.answer(
            "Режим: 📄 документ/фото → PDF.\n"
            "Пришли офисный документ (DOCX, XLSX, PPTX) или картинку (как фото или как файл).",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Mode for {message.from_user.id} = doc_photo")

    # ===== PDF: в зависимости от режима — сжатие ИЛИ извлечение текста =====

    @dp.message(F.document & (F.document.mime_type == "application/pdf"))
    async def handle_pdf(message: types.Message):
        user_id = message.from_user.id
        mode = user_modes.get(user_id, "compress")
        doc = message.document

        logger.info(f"PDF from {user_id}, mode={mode}")

        file = await bot.get_file(doc.file_id)
        src_path = FILES_DIR / doc.file_name
        await bot.download_file(file.file_path, destination=src_path)

        # --- РЕЖИМ: PDF -> текст ---
        if mode == "pdf_text":
            await message.answer("Извлекаю текст из PDF...")
            text_chunks = []

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
                await message.answer("В этом PDF не удалось найти текст (возможно, это скан).")
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

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
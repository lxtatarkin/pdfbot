import asyncio
import subprocess
from pathlib import Path
import os
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv

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


async def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set in environment")
        return

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    logger.info("Bot started")

    @dp.message(Command("start"))
    async def start_cmd(message: types.Message):
        logger.info(f"/start from {message.from_user.id} ({message.from_user.username})")
        text = (
            "👋 Привет! Я конвертирую файлы в PDF прямо в Telegram.\n\n"
            "Что я умею:\n"
            "• Фото → PDF\n"
            "• DOC / DOCX → PDF\n"
            "• XLS / XLSX → PDF\n"
            "• PPT / PPTX → PDF\n"
            "• Сжатие PDF\n\n"
            "Просто отправьте файл (фото, документ или PDF) — я верну результат."
        )
        await message.answer(text)

    # === Приём PDF и глубокое сжатие (Ghostscript) ===
    @dp.message(F.document & (F.document.mime_type == "application/pdf"))
    async def handle_pdf(message: types.Message):
        logger.info(f"PDF received for compression from {message.from_user.id}")

        doc = message.document
        file = await bot.get_file(doc.file_id)

        src_path = FILES_DIR / doc.file_name
        await bot.download_file(file.file_path, destination=src_path)

        await message.answer("Сжимаю PDF... (глубокое сжатие)")

        compressed_path = FILES_DIR / f"compressed_{doc.file_name}"

        # Команда Ghostscript
        gs_cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",   # варианты: /screen /ebook /printer /prepress
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

        if not compressed_path.exists():
            logger.error("Ghostscript did not create compressed file")
            await message.answer("Не удалось сжать PDF.")
            return

        await message.answer_document(
            types.FSInputFile(compressed_path),
            caption="Готово: PDF-файл глубоко сжат."
        )
        logger.info("PDF deeply compressed with Ghostscript")

    # === Приём документов (КРОМЕ PDF) и конвертация в PDF ===
    @dp.message(F.document & (F.document.mime_type != "application/pdf"))
    async def handle_document(message: types.Message):
        doc = message.document
        filename = doc.file_name or "file"
        ext = filename.split(".")[-1].lower()
        logger.info(f"DOC ({ext}) from {message.from_user.id}")

        supported = {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}

        if ext not in supported:
            await message.answer(
                "Документ сохранён.\n"
                "Пока я умею конвертировать в PDF только форматы: DOC, DOCX, XLS, XLSX, PPT, PPTX."
            )
            return

        file = await bot.get_file(doc.file_id)
        src_path = FILES_DIR / filename
        await bot.download_file(file.file_path, destination=src_path)

        await message.answer("Конвертирую документ в PDF, подождите несколько секунд...")

        # Выбираем путь к LibreOffice в зависимости от ОС
        if os.name == "nt":
            # Windows (локальный запуск)
            lo_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
        else:
            # Linux (Railway / Docker)
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

    # Приём фото и конвертация в PDF, сохраняем имя файла
    @dp.message(F.photo)
    async def handle_photo(message: types.Message):
        logger.info(f"PHOTO from {message.from_user.id}")
        from PIL import Image

        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)

        # Для обычного фото Telegram не даёт оригинальное имя файла.
        # Делаем понятное имя: photo_<id>.jpg → photo_<id>.pdf
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
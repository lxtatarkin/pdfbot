import asyncio
import subprocess
from pathlib import Path
import os
import time
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv

# Загрузка переменных окружения
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


# =========================
#     ОЧИСТКА ФАЙЛОВ
# =========================
def cleanup_old_files():
    now = time.time()
    expire = 60 * 60 * 2  # 2 часа

    for file in FILES_DIR.iterdir():
        try:
            if file.is_file() and now - file.stat().st_mtime > expire:
                file.unlink()
                logger.info(f"Deleted old file: {file.name}")
        except Exception:
            pass


# =========================
#     НАЧАЛО MAIN()
# =========================
async def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set in environment")
        return

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    logger.info("Bot started")

    # Периодическая очистка файлов
    async def periodic_cleanup():
        while True:
            cleanup_old_files()
            await asyncio.sleep(600)  # каждые 10 минут

    asyncio.create_task(periodic_cleanup())

    # =========================
    #        /start
    # =========================
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
            "Просто отправьте файл — я сам определю, что делать."
        )
        await message.answer(text)

    # =========================
    #        /help
    # =========================
    @dp.message(Command("help"))
    async def help_cmd(message: types.Message):
        await message.answer(
            "📘 <b>Функции бота</b>\n\n"
            "• Фото → PDF\n"
            "• DOC/DOCX → PDF\n"
            "• XLS/XLSX → PDF\n"
            "• PPT/PPTX → PDF\n"
            "• Сжатие PDF (глубокое)\n"
            "• Автоочистка временных файлов\n"
            "• Лимит размера: 20 МБ\n\n"
            "Отправьте любой файл — бот всё сделает.",
            parse_mode="HTML"
        )

    # =========================
    #      Сжатие PDF (GS)
    # =========================
    @dp.message(F.document & (F.document.mime_type == "application/pdf"))
    async def handle_pdf(message: types.Message):
        doc = message.document

        # Лимит размера
        if doc.file_size and doc.file_size > 20 * 1024 * 1024:
            await message.answer("Файл слишком большой. Максимум 20 МБ.")
            return

        logger.info(f"PDF received for compression from {message.from_user.id}")

        file = await bot.get_file(doc.file_id)

        src_path = FILES_DIR / doc.file_name
        await bot.download_file(file.file_path, destination=src_path)

        await message.answer("Сжимаю PDF... (глубокое сжатие)")

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
            logger.error(f"Ghostscript error: {e}")
            await message.answer("Ошибка при сжатии PDF.")
            return

        if not compressed_path.exists():
            logger.error("Compressed PDF not created")
            await message.answer("Не удалось сжать PDF.")
            return

        await message.answer_document(
            types.FSInputFile(compressed_path),
            caption="Готово: PDF-файл глубоко сжат."
        )
        logger.info("PDF deeply compressed")

    # =========================
    #    Документы → PDF
    # =========================
    @dp.message(F.document & (F.document.mime_type != "application/pdf"))
    async def handle_document(message: types.Message):
        doc = message.document
        filename = doc.file_name or "file"
        ext = filename.split(".")[-1].lower()

        # Лимит размера
        if doc.file_size and doc.file_size > 20 * 1024 * 1024:
            await message.answer("Файл слишком большой. Максимум 20 МБ.")
            return

        logger.info(f"DOC ({ext}) from {message.from_user.id}")

        supported = {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}

        if ext not in supported:
            await message.answer(
                "Документ сохранён.\n"
                "Но конвертация в PDF возможна только для:\n"
                "DOC, DOCX, XLS, XLSX, PPT, PPTX."
            )
            return

        file = await bot.get_file(doc.file_id)
        src_path = FILES_DIR / filename
        await bot.download_file(file.file_path, destination=src_path)

        await message.answer("Конвертирую документ в PDF...")

        if os.name == "nt":
            lo_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
        else:
            lo_path = "soffice"

        logger.info(f"Using LibreOffice: {lo_path}")

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
            await message.answer("Ошибка конвертации (subprocess).")
            return

        if result.returncode != 0:
            logger.error(f"LibreOffice error: {result.stderr}")
            await message.answer("Не удалось конвертировать документ.")
            return

        pdf_name = Path(filename).with_suffix(".pdf").name
        pdf_path = FILES_DIR / pdf_name

        if not pdf_path.exists():
            logger.error(f"Converted PDF missing: {pdf_path}")
            await message.answer("Ошибка: PDF не найден после конвертации.")
            return

        await message.answer_document(
            types.FSInputFile(pdf_path),
            caption="Готово: документ конвертирован в PDF."
        )
        logger.info("Document converted to PDF")

    # =========================
    #       Фото → PDF
    # =========================
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
            caption="Фото конвертировано в PDF."
        )
        logger.info("Photo converted to PDF")

    await dp.start_polling(bot)


# =========================
#       RUN
# =========================
if __name__ == "__main__":
    asyncio.run(main())
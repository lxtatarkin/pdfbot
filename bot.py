import asyncio
import subprocess
from pathlib import Path
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv

# грузим .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Папка для файлов
BASE_DIR = Path(__file__).parent
FILES_DIR = BASE_DIR / "files"
FILES_DIR.mkdir(exist_ok=True)


async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start_cmd(message: types.Message):
        text = (
            "👋 Привет! Я конвертирую файлы в PDF прямо в Telegram.\n\n"
            "Что я уже умею:\n"
            "• Фото → PDF\n"
            "• DOC / DOCX → PDF\n"
            "• XLS / XLSX → PDF\n"
            "• PPT / PPTX → PDF\n\n"
            "Просто отправьте мне файл (документ или фото), и я верну PDF."
        )
        await message.answer(text)

        # === Приём PDF и сжатие ===
    @dp.message(F.document & (F.document.mime_type == "application/pdf"))
    async def handle_pdf(message: types.Message):
        from pikepdf import Pdf

        doc = message.document
        file = await bot.get_file(doc.file_id)

        src_path = FILES_DIR / doc.file_name
        await bot.download_file(file.file_path, destination=src_path)

        await message.answer("Сжимаю PDF...")

        compressed_path = FILES_DIR / f"compressed_{doc.file_name}"

        try:
            # Просто пересохраняем PDF — это базовое сжатие
            with Pdf.open(src_path) as pdf:
                pdf.save(compressed_path)

            await message.answer_document(
                types.FSInputFile(compressed_path),
                caption="Готово: PDF-файл сжат."
            )

        except Exception as e:
            print(f"PDF compress error: {e}")
            await message.answer(
                "Не удалось сжать PDF, отправляю оригинальный файл."
            )
            await message.answer_document(
                types.FSInputFile(src_path),
                caption="Возвращаю оригинальный PDF."
            )

    # === ПОТОМ: приём документов (КРОМЕ PDF) и конвертация в PDF ===
    @dp.message(F.document & (F.document.mime_type != "application/pdf"))
    async def handle_document(message: types.Message):
        doc = message.document
        filename = doc.file_name or "file"
        ext = filename.split(".")[-1].lower()

        supported = {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}

        file = await bot.get_file(doc.file_id)
        src_path = FILES_DIR / filename
        await bot.download_file(file.file_path, destination=src_path)

        if ext not in supported:
            await message.answer(
                "Документ сохранён.\n"
                "Пока я умею конвертировать в PDF только форматы: DOC, DOCX, XLS, XLSX, PPT, PPTX."
            )
            return

        await message.answer("Конвертирую документ в PDF, подождите несколько секунд...")

        # Путь к LibreOffice (по умолчанию для Windows)
        lo_path = r"C:\Program Files\LibreOffice\program\soffice.exe"

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

        if result.returncode != 0:
            await message.answer("Произошла ошибка при конвертации документа.")
            return

        pdf_name = Path(filename).with_suffix(".pdf").name
        pdf_path = FILES_DIR / pdf_name

        if not pdf_path.exists():
            await message.answer("PDF-файл не найден после конвертации.")
            return

        await message.answer_document(
            types.FSInputFile(pdf_path),
            caption="Готово: документ сконвертирован в PDF."
        )

    # Приём фото и конвертация в PDF
    @dp.message(F.photo)
    async def handle_photo(message: types.Message):
        from PIL import Image  # импорт внутри хэндлера

        photo = message.photo[-1]  # самое большое по размеру
        file = await bot.get_file(photo.file_id)

        # Сохраняем оригинальное фото
        jpg_path = FILES_DIR / f"{photo.file_id}.jpg"
        await bot.download_file(file.file_path, destination=jpg_path)

        # Конвертация в PDF
        pdf_path = FILES_DIR / f"{photo.file_id}.pdf"
        image = Image.open(jpg_path).convert("RGB")
        image.save(pdf_path, "PDF")

        # Отправляем PDF пользователю
        await message.answer_document(
            types.FSInputFile(pdf_path),
            caption="Фото сконвертировано в PDF."
        )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
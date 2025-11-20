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
PRO_USERS_RAW = os.getenv("PRO_USERS", "")

# Множество PRO-пользователей (ID телеграма)
PRO_USERS: set[int] = set()
for part in PRO_USERS_RAW.split(","):
    part = part.strip()
    if part.isdigit():
        PRO_USERS.add(int(part))

# FREE / PRO лимиты (в байтах)
FREE_MAX_SIZE = 20 * 1024 * 1024      # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024      # 100 MB

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


def is_pro(user_id: int) -> bool:
    return user_id in PRO_USERS


def get_user_limit(user_id: int) -> int:
    return PRO_MAX_SIZE if is_pro(user_id) else FREE_MAX_SIZE


def format_mb(bytes_size: int) -> str:
    return f"{bytes_size / (1024 * 1024):.0f} МБ"


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
#     MAIN
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
        user_id = message.from_user.id
        tier = "PRO" if is_pro(user_id) else "FREE"
        limit_mb = format_mb(get_user_limit(user_id))

        logger.info(f"/start from {user_id} ({message.from_user.username}), tier={tier}")
        text = (
            "👋 Привет! Я конвертирую файлы в PDF прямо в Telegram.\n\n"
            "Что я умею:\n"
            "• Фото → PDF\n"
            "• DOC / DOCX → PDF\n"
            "• XLS / XLSX → PDF\n"
            "• PPT / PPTX → PDF\n"
            "• Сжатие PDF\n\n"
            f"Текущий тариф: <b>{tier}</b>\n"
            f"Максимальный размер файла: <b>{limit_mb}</b>\n\n"
            "Отправьте файл — я сам определю, что делать.\n"
            "Команда /help — описание функций.\n"
            "Команда /pro — как получить PRO."
        )
        await message.answer(text, parse_mode="HTML")

    # =========================
    #        /help
    # =========================
    @dp.message(Command("help"))
    async def help_cmd(message: types.Message):
        user_id = message.from_user.id
        tier = "PRO" if is_pro(user_id) else "FREE"
        limit_mb = format_mb(get_user_limit(user_id))

        await message.answer(
            "📘 <b>Функции бота</b>\n\n"
            "• Фото → PDF\n"
            "• DOC/DOCX → PDF\n"
            "• XLS/XLSX → PDF\n"
            "• PPT/PPTX → PDF\n"
            "• Сжатие PDF (глубокое)\n\n"
            f"Ваш тариф: <b>{tier}</b>\n"
            f"Лимит размера файла: <b>{limit_mb}</b>\n\n"
            "FREE: до 20 МБ\n"
            "PRO: до 100 МБ и приоритет обработки.\n\n"
            "Команда /pro — детали PRO.",
            parse_mode="HTML"
        )

    # =========================
    #        /pro
    # =========================
    @dp.message(Command("pro"))
    async def pro_cmd(message: types.Message):
        user_id = message.from_user.id
        if is_pro(user_id):
            await message.answer(
                "✅ У вас уже активен <b>PRO</b>-доступ.\n\n"
                "• Лимит файла: до 100 МБ\n"
                "• Приоритет обработки\n\n"
                "Спасибо за поддержку!",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "💼 <b>PRO-версия бота</b>\n\n"
                "Преимущества:\n"
                "• Лимит файла: до 100 МБ (вместо 20 МБ)\n"
                "• Приоритет обработки\n"
                "• В будущем: OCR (распознавание сканов), водяные знаки и др.\n\n"
                "Сейчас PRO подключается вручную.\n"
                "Напишите владельцу бота, чтобы получить подробности.",
                parse_mode="HTML"
            )

    # =========================
    #   Общая проверка лимита
    # =========================
    async def check_size_or_reject(message: types.Message, doc: types.Document) -> bool:
        """Возвращает True, если можно обрабатывать; False, если надо прервать."""
        user_id = message.from_user.id
        max_size = get_user_limit(user_id)
        tier = "PRO" if is_pro(user_id) else "FREE"

        if doc.file_size and doc.file_size > max_size:
            user_limit_mb = format_mb(max_size)
            await message.answer(
                f"Файл слишком большой для вашего тарифа ({tier}).\n"
                f"Текущий лимит: {user_limit_mb}.\n\n"
                "Для работы с более крупными файлами нужен PRO-доступ.\n"
                "Команда /pro — подробности."
            )
            logger.info(
                f"User {user_id} exceeded size limit: size={doc.file_size}, limit={max_size}, tier={tier}"
            )
            return False

        return True

    # =========================
    #      Сжатие PDF (GS)
    # =========================
    @dp.message(F.document & (F.document.mime_type == "application/pdf"))
    async def handle_pdf(message: types.Message):
        doc = message.document

        if not await check_size_or_reject(message, doc):
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

        if not await check_size_or_reject(message, doc):
            return

        logger.info(f"DOC ({ext}) from {message.from_user.id}")

        supported = {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}

        # Изображения, отправленные как файл (image/*), можно позже тоже сделать платной опцией, если захочешь
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
                caption="Изображение конвертировано в PDF."
            )
            logger.info("IMAGE-DOC converted to PDF")
            return

        if ext not in supported:
            await message.answer(
                "Документ сохранён.\n"
                "Но конвертация в PDF возможна только для:\n"
                "DOC, DOCX, XLS, XLSX, PPT, PPTX\n"
                "и изображений, отправленных как файл."
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


if __name__ == "__main__":
    asyncio.run(main())
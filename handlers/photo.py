from aiogram import Router, types, F, Bot

from settings import FILES_DIR
from pdf_services import image_file_to_pdf
from utils import check_size_or_reject
from state import user_modes
from i18n import t

router = Router()


@router.message(F.photo)
async def handle_photo(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    mode = user_modes.get(user_id, "doc_photo")  # пока режим не используем, но может пригодиться

    photo = message.photo[-1]

    # проверка лимита по размеру
    if not await check_size_or_reject(message, photo.file_size):
        return

    await message.answer(t(user_id, "msg_converting_image"))

    file = await bot.get_file(photo.file_id)

    filename = f"photo_{user_id}_{photo.file_id}.jpg"
    src_path = FILES_DIR / filename
    await bot.download_file(file.file_path, destination=src_path)

    pdf_path = image_file_to_pdf(src_path)
    if not pdf_path:
        await message.answer(t(user_id, "err_image_convert"))
        return

    await message.answer_document(
        types.FSInputFile(pdf_path),
        caption=t(user_id, "msg_done"),
    )

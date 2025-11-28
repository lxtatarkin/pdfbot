from pathlib import Path
import zipfile

from aiogram import Router, types, F, Bot
from PyPDF2 import PdfReader, PdfWriter
from keyboards import get_pages_menu_keyboard, get_merge_keyboard

from settings import (
    get_user_limit,
    is_pro,
    format_mb,
    FILES_DIR,
    logger,
)
from state import (
    user_modes,
    user_merge_files,
    user_watermark_state,
    user_pages_state,
)
from keyboards import get_pages_menu_keyboard
from pdf_services import (
    ocr_pdf_to_txt,
    create_searchable_pdf,
    split_pdf_to_pages,
    extract_text_from_pdf,
    compress_pdf,
)
from i18n import t

router = Router()


async def check_size_or_reject(message: types.Message, size_bytes: int | None) -> bool:
    """Проверка лимита размера файла для FREE/PRO."""
    user_id = message.from_user.id
    max_size = get_user_limit(user_id)
    tier = "PRO" if is_pro(user_id) else "FREE"

    if size_bytes is not None and size_bytes > max_size:
        await message.answer(
            t(
                user_id,
                "err_file_too_big",
                tier=tier,
                limit=format_mb(max_size),
            )
        )
        logger.info(
            f"User {user_id} exceeded size limit: file={size_bytes}, limit={max_size}"
        )
        return False

    return True


@router.message(F.document & (F.document.mime_type == "application/pdf"))
async def handle_pdf(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    mode = user_modes.get(user_id, "compress")
    doc_msg = message.document

    # Проверка размера
    if not await check_size_or_reject(message, doc_msg.file_size):
        return

    # Скачиваем PDF во временную папку
    file = await bot.get_file(doc_msg.file_id)
    src_path = FILES_DIR / doc_msg.file_name
    await bot.download_file(file.file_path, destination=src_path)

    # =============================
    # РЕДАКТОР СТРАНИЦ: новый PDF
    # =============================
    if mode.startswith("pages"):
        if not is_pro(user_id):
            await message.answer(t(user_id, "pages_pro_only_full"))
            return

        try:
            reader = PdfReader(str(src_path))
            num_pages = len(reader.pages)
        except Exception as e:
            logger.error(f"Pages editor open error: {e}")
            await message.answer(t(user_id, "err_open_pdf"))
            return

        user_pages_state[user_id] = {
            "pdf_path": src_path,
            "pages": num_pages,
        }
        user_modes[user_id] = "pages_menu"

        await message.answer(
            t(
                user_id,
                "pages_intro_with_file",
                file_name=doc_msg.file_name,
                num_pages=num_pages,
            ),
            reply_markup=get_pages_menu_keyboard(user_id),
        )
        return

    # =============================
    # PRO: OCR ДЛЯ PDF
    # =============================
    if mode == "ocr":
        if not is_pro(user_id):
            await message.answer(t(user_id, "ocr_pro_only"))
            return

        await message.answer(t(user_id, "msg_ocr_processing"))

        txt_path = ocr_pdf_to_txt(src_path, user_id, lang="rus+eng")
        if not txt_path:
            await message.answer(t(user_id, "err_ocr_failed"))
            return

        await message.answer_document(
            types.FSInputFile(txt_path),
            caption=t(user_id, "msg_ocr_done"),
        )
        logger.info(f"OCR PDF done for user {user_id}")
        return

    # =============================
    # PRO: Searchable PDF
    # =============================
    if mode == "searchable_pdf":
        if not is_pro(user_id):
            await message.answer(t(user_id, "searchable_pro_only"))
            return

        await message.answer(t(user_id, "msg_searchable_processing"))

        out_path = create_searchable_pdf(src_path, lang="rus+eng")
        if not out_path:
            await message.answer(t(user_id, "err_searchable_failed"))
            return

        await message.answer_document(
            types.FSInputFile(out_path),
            caption=t(user_id, "msg_searchable_done"),
        )
        logger.info(f"Searchable PDF done for user {user_id}")
        return

    # =============================
    # WATERMARK STEP 1: получить PDF
    # =============================
    if mode == "watermark":
        if not is_pro(user_id):
            await message.answer(t(user_id, "wm_pro_only"))
            return

        user_watermark_state[user_id] = {"pdf_path": src_path}
        user_modes[user_id] = "watermark_wait_text"

        await message.answer(t(user_id, "wm_pdf_received"))
        return

    # =============================
    # MERGE MODE: просто копим PDF
    # =============================
    if mode == "merge":
        files_list = user_merge_files.setdefault(user_id, [])
        if len(files_list) >= 10:
            await message.answer(t(user_id, "merge_too_many"))
            return

        files_list.append(src_path)
        count = len(files_list)

        # показываем кнопку "Объединить", когда файлов >= 2
        if count >= 2:
            kb = get_merge_keyboard(user_id)
        else:
            kb = None

        await message.answer(
            t(
                user_id,
                "merge_file_added",
                count=count,
            ),
            reply_markup=kb,
        )
        return

    # =============================
    # PDF → TEXT
    # =============================
    if mode == "pdf_text":
        await message.answer(t(user_id, "msg_extracting_text"))

        text_full = extract_text_from_pdf(src_path)
        if not text_full:
            await message.answer(t(user_id, "err_no_text_found"))
            return

        txt_path = FILES_DIR / (Path(doc_msg.file_name).stem + ".txt")
        txt_path.write_text(text_full, encoding="utf-8")

        await message.answer_document(
            types.FSInputFile(txt_path),
            caption=t(user_id, "msg_done"),
        )
        return

    # =============================
    # SPLIT PDF
    # =============================
    if mode == "split":
        await message.answer(t(user_id, "msg_splitting_pdf"))

        pages = split_pdf_to_pages(src_path)
        if pages is None:
            await message.answer(t(user_id, "err_open_pdf"))
            return

        if len(pages) <= 1:
            await message.answer(t(user_id, "err_only_one_page"))
            return

        n = len(pages)

        if n <= 10:
            for i, p in enumerate(pages, start=1):
                await message.answer_document(
                    types.FSInputFile(p),
                    caption=t(user_id, "split_page_caption", i=i, n=n),
                )
        else:
            zip_path = FILES_DIR / f"{src_path.stem}_pages.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in pages:
                    zf.write(p, arcname=p.name)

            await message.answer_document(
                types.FSInputFile(zip_path),
                caption=t(user_id, "split_zip_done", n=n),
            )
        return

    # =============================
    # COMPRESS PDF (DEFAULT)
    # =============================
    await message.answer(t(user_id, "msg_compressing_pdf"))
    compressed_path = FILES_DIR / f"compressed_{doc_msg.file_name}"

    ok = compress_pdf(src_path, compressed_path)
    if not ok:
        await message.answer(t(user_id, "err_compress_failed"))
        return

    await message.answer_document(
        types.FSInputFile(compressed_path),
        caption=t(user_id, "msg_done"),
    )

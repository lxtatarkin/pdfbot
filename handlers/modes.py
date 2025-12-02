# handlers/modes.py
from aiogram import Router, types, F

from state import (
    user_modes,
    user_merge_files,
    user_watermark_state,
    user_pages_state,
)
from keyboards import get_main_keyboard
from settings import is_pro
from i18n import t, TEXTS

router = Router()

# Тексты кнопок для обоих языков (чтобы фильтровать по ним)
COMPRESS_TEXTS = {
    TEXTS["ru"]["btn_main_compress"],
    TEXTS["en"]["btn_main_compress"],
}
PDF_TEXT_TEXTS = {
    TEXTS["ru"]["btn_main_pdf_to_text"],
    TEXTS["en"]["btn_main_pdf_to_text"],
}
DOC_PHOTO_TEXTS = {
    TEXTS["ru"]["btn_main_doc_to_pdf"],
    TEXTS["en"]["btn_main_doc_to_pdf"],
}
MERGE_TEXTS = {
    TEXTS["ru"]["btn_main_merge"],
    TEXTS["en"]["btn_main_merge"],
}
SPLIT_TEXTS = {
    TEXTS["ru"]["btn_main_split"],
    TEXTS["en"]["btn_main_split"],
}
OCR_TEXTS = {
    TEXTS["ru"]["btn_main_ocr"],
    TEXTS["en"]["btn_main_ocr"],
}
SEARCHABLE_TEXTS = {
    TEXTS["ru"]["btn_main_searchable"],
    TEXTS["en"]["btn_main_searchable"],
}
PAGES_TEXTS = {
    TEXTS["ru"]["btn_main_pages"],
    TEXTS["en"]["btn_main_pages"],
}
WATERMARK_TEXTS = {
    TEXTS["ru"]["btn_main_watermark"],
    TEXTS["en"]["btn_main_watermark"],
}


def reset_user_state(user_id: int):
    user_modes[user_id] = "compress"
    user_merge_files[user_id] = []
    user_watermark_state[user_id] = {}
    user_pages_state[user_id] = {}


@router.message(F.text.in_(COMPRESS_TEXTS))
async def mode_compress(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)
    user_modes[user_id] = "compress"

    await message.answer(
        t(user_id, "mode_compress"),
        reply_markup=get_main_keyboard(user_id),
    )


@router.message(F.text.in_(PDF_TEXT_TEXTS))
async def mode_pdf_text(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)
    user_modes[user_id] = "pdf_text"

    await message.answer(
        t(user_id, "mode_pdf_text"),
        reply_markup=get_main_keyboard(user_id),
    )


@router.message(F.text.in_(DOC_PHOTO_TEXTS))
async def mode_doc_photo(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)
    user_modes[user_id] = "doc_photo"

    await message.answer(
        t(user_id, "mode_doc_photo"),
        reply_markup=get_main_keyboard(user_id),
    )


@router.message(F.text.in_(MERGE_TEXTS))
async def mode_merge(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)
    user_modes[user_id] = "merge"

    await message.answer(
        t(user_id, "mode_merge"),
        reply_markup=get_main_keyboard(user_id),
    )


@router.message(F.text.in_(SPLIT_TEXTS))
async def mode_split(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)
    user_modes[user_id] = "split"

    await message.answer(
        t(user_id, "mode_split"),
        reply_markup=get_main_keyboard(user_id),
    )


@router.message(F.text.in_(OCR_TEXTS))
async def mode_ocr(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)
    user_modes[user_id] = "ocr"

    if not await is_pro(user_id):
        await message.answer(
            t(user_id, "mode_ocr_free"),
            reply_markup=get_main_keyboard(user_id),
        )
    else:
        await message.answer(
            t(user_id, "mode_ocr_pro"),
            reply_markup=get_main_keyboard(user_id),
        )


@router.message(F.text.in_(SEARCHABLE_TEXTS))
async def mode_searchable_pdf(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)
    user_modes[user_id] = "searchable_pdf"

    if not await is_pro(user_id):
        await message.answer(
            t(user_id, "mode_searchable_free"),
            reply_markup=get_main_keyboard(user_id),
        )
    else:
        await message.answer(
            t(user_id, "mode_searchable_pro"),
            reply_markup=get_main_keyboard(user_id),
        )


@router.message(F.text.in_(PAGES_TEXTS))
async def mode_pages(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)

    if not await is_pro(user_id):
        user_modes[user_id] = "compress"
        await message.answer(
            t(user_id, "mode_pages_free"),
            reply_markup=get_main_keyboard(user_id),
        )
    else:
        user_modes[user_id] = "pages_wait_pdf"
        await message.answer(
            t(user_id, "mode_pages_pro"),
            reply_markup=get_main_keyboard(user_id),
        )


@router.message(F.text.in_(WATERMARK_TEXTS))
async def mode_watermark(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)
    user_modes[user_id] = "watermark"

    if not await is_pro(user_id):
        await message.answer(
            t(user_id, "mode_watermark_free"),
            reply_markup=get_main_keyboard(user_id),
        )
    else:
        await message.answer(
            t(user_id, "mode_watermark_pro"),
            reply_markup=get_main_keyboard(user_id),
        )

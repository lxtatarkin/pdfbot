# handlers/pages.py
from pathlib import Path

from aiogram import Router, types, F
from PyPDF2 import PdfReader, PdfWriter

from settings import FILES_DIR, logger, is_pro
from state import user_modes, user_pages_state
from keyboards import get_pages_menu_keyboard, get_rotate_keyboard
from pdf_services import rotate_page_inplace
from i18n import t

router = Router()


@router.callback_query(F.data == "pages_action:rotate")
async def pages_rotate_action(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = user_pages_state.get(user_id) or {}
    pdf_path = state.get("pdf_path")
    num_pages = state.get("pages")

    if not await is_pro(user_id):
        await callback.answer(t(user_id, "pages_pro_only"), show_alert=True)
        return

    if not pdf_path or not Path(pdf_path).exists() or not num_pages:
        await callback.answer(t(user_id, "pages_no_pdf_editor"), show_alert=True)
        return

    if num_pages == 1:
        # одна страница — сразу угол
        state["rotate_pages"] = [1]
        user_pages_state[user_id] = state
        user_modes[user_id] = "pages_rotate_wait_angle"

        await callback.message.answer(
            t(user_id, "pages_one_page_choose_angle"),
            reply_markup=get_rotate_keyboard(user_id),
        )
    else:
        # несколько страниц — сначала спросить диапазон
        user_modes[user_id] = "pages_rotate_wait_pages"
        await callback.message.answer(
            t(user_id, "pages_rotate_ask_pages", num_pages=num_pages)
        )

    await callback.answer()


@router.callback_query(F.data == "pages_action:delete")
async def pages_delete_action(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = user_pages_state.get(user_id) or {}
    pdf_path = state.get("pdf_path")
    num_pages = state.get("pages")

    if not await is_pro(user_id):
        await callback.answer(t(user_id, "pages_pro_only"), show_alert=True)
        return

    if not pdf_path or not Path(pdf_path).exists() or not num_pages:
        await callback.answer(t(user_id, "pages_no_pdf"), show_alert=True)
        return

    user_modes[user_id] = "pages_delete_wait_pages"
    await callback.message.answer(
        t(user_id, "pages_delete_ask_pages", num_pages=num_pages)
    )
    await callback.answer()


@router.callback_query(F.data == "pages_action:extract")
async def pages_extract_action(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = user_pages_state.get(user_id) or {}
    pdf_path = state.get("pdf_path")
    num_pages = state.get("pages")

    if not await is_pro(user_id):
        await callback.answer(t(user_id, "pages_pro_only"), show_alert=True)
        return

    if not pdf_path or not Path(pdf_path).exists() or not num_pages:
        await callback.answer(t(user_id, "pages_no_pdf"), show_alert=True)
        return

    user_modes[user_id] = "pages_extract_wait_pages"
    await callback.message.answer(
        t(user_id, "pages_extract_ask_pages", num_pages=num_pages)
    )
    await callback.answer()


@router.callback_query(F.data == "pages_action:cancel")
async def pages_cancel_action(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_pages_state[user_id] = {}
    user_modes[user_id] = "compress"

    await callback.message.answer(
        t(user_id, "pages_edit_finished")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pages_rotate_angle:"))
async def pages_rotate_angle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data.split(":", 1)[1]

    try:
        angle = int(data)
    except ValueError:
        await callback.answer(t(user_id, "pages_bad_angle"), show_alert=True)
        return

    state = user_pages_state.get(user_id) or {}
    pdf_path = state.get("pdf_path")
    num_pages = state.get("pages")

    if not await is_pro(user_id):
        await callback.answer(t(user_id, "pages_pro_only"), show_alert=True)
        return

    if not pdf_path or not Path(pdf_path).exists() or not num_pages:
        await callback.answer(t(user_id, "pages_no_pdf_short"), show_alert=True)
        user_modes[user_id] = "compress"
        return

    rotate_pages = state.get("rotate_pages") or list(range(1, num_pages + 1))

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        logger.error(f"Pages rotate open error: {e}")
        await callback.message.answer(t(user_id, "pages_open_error"))
        await callback.answer()
        return

    writer = PdfWriter()
    rotate_set = set(rotate_pages)

    for idx, page in enumerate(reader.pages, start=1):
        if idx in rotate_set:
            rotate_page_inplace(page, angle)
        writer.add_page(page)

    out_path = FILES_DIR / f"{Path(pdf_path).stem}_rotated.pdf"

    try:
        with open(out_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        logger.error(f"Pages rotate write error: {e}")
        await callback.message.answer(t(user_id, "pages_save_error"))
        await callback.answer()
        return

    await callback.message.answer_document(
        types.FSInputFile(out_path),
        caption=t(user_id, "pages_rotated_done", angle=angle),
    )

    # Обновляем состояние
    state["pdf_path"] = out_path
    state["pages"] = num_pages
    state.pop("rotate_pages", None)
    user_pages_state[user_id] = state
    user_modes[user_id] = "pages_menu"

    await callback.message.answer(
        t(user_id, "pages_continue_choose_action"),
        reply_markup=get_pages_menu_keyboard(user_id),
    )
    await callback.answer()


@router.callback_query(F.data == "pages_back_to_menu")
async def pages_back_to_menu_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = user_pages_state.get(user_id) or {}
    pdf_path = state.get("pdf_path")
    num_pages = state.get("pages")

    if not pdf_path or not Path(pdf_path).exists() or not num_pages:
        user_modes[user_id] = "compress"
        await callback.message.answer(
            t(user_id, "pages_no_active_doc")
        )
    else:
        user_modes[user_id] = "pages_menu"
        await callback.message.answer(
            t(user_id, "pages_menu_header", num_pages=num_pages),
            reply_markup=get_pages_menu_keyboard(user_id),
        )

    await callback.answer()

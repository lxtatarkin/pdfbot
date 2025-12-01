from pathlib import Path

from aiogram import Router, types, F
from PyPDF2 import PdfReader, PdfWriter, PdfMerger

from settings import FILES_DIR, logger
from state import (
    user_modes,
    user_merge_files,
    user_watermark_state,
    user_pages_state,
)
from keyboards import (
    get_pages_menu_keyboard,
    get_rotate_keyboard,
    get_watermark_keyboard,
)
from pdf_services import parse_page_range
from i18n import t  # ЛОКАЛИЗАЦИЯ

router = Router()


# любые текстовые сообщения, КРОМЕ команд (строк, начинающихся с "/")
@router.message(F.text, ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    mode = user_modes.get(user_id, "compress")
    text_raw = (message.text or "").strip()
    text_val = text_raw.lower()

    # ===== РЕДАКТОР СТРАНИЦ: ввод диапазона для ПОВОРОТА =====
    if mode == "pages_rotate_wait_pages":
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await message.answer(t(user_id, "pages_no_pdf_editor"))
            user_modes[user_id] = "compress"
            return

        if text_val == "all":
            pages = list(range(1, num_pages + 1))
        else:
            pages = parse_page_range(text_raw, num_pages)

        if not pages:
            await message.answer(t(user_id, "pages_rotate_range_failed"))
            return

        state["rotate_pages"] = pages
        user_pages_state[user_id] = state
        user_modes[user_id] = "pages_rotate_wait_angle"

        await message.answer(
            t(user_id, "pages_rotate_confirm", raw=text_raw),
            reply_markup=get_rotate_keyboard(user_id),
        )
        return

    # ===== РЕДАКТОР СТРАНИЦ: ожидание угла (просим пользоваться кнопками) =====
    if mode == "pages_rotate_wait_angle":
        await message.answer(t(user_id, "pages_angle_reminder"))
        return

    # ===== РЕДАКТОР СТРАНИЦ: ввод диапазона для УДАЛЕНИЯ =====
    if mode == "pages_delete_wait_pages":
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await message.answer(t(user_id, "pages_no_pdf_editor"))
            user_modes[user_id] = "compress"
            return

        pages = parse_page_range(text_raw, num_pages)
        if not pages:
            await message.answer(t(user_id, "pages_delete_range_failed"))
            return

        delete_set = set(pages)

        try:
            reader = PdfReader(str(pdf_path))
        except Exception as e:
            logger.error(f"Pages delete open error: {e}")
            await message.answer(t(user_id, "pages_open_error"))
            return

        writer = PdfWriter()
        kept = 0
        for idx, page in enumerate(reader.pages, start=1):
            if idx in delete_set:
                continue
            writer.add_page(page)
            kept += 1

        if kept == 0:
            await message.answer(t(user_id, "pages_delete_all_removed"))
            user_modes[user_id] = "pages_menu"
            return

        out_path = FILES_DIR / f"{Path(pdf_path).stem}_deleted.pdf"
        try:
            with open(out_path, "wb") as f:
                writer.write(f)
        except Exception as e:
            logger.error(f"Pages delete write error: {e}")
            await message.answer(t(user_id, "pages_save_error"))
            return

        await message.answer_document(
            types.FSInputFile(out_path),
            caption=t(user_id, "pages_delete_done", raw=text_raw, kept=kept),
        )

        user_pages_state[user_id] = {
            "pdf_path": out_path,
            "pages": kept,
        }
        user_modes[user_id] = "pages_menu"

        await message.answer(
            t(user_id, "pages_continue_editing_full"),
            reply_markup=get_pages_menu_keyboard(user_id),
        )
        return

    # ===== РЕДАКТОР СТРАНИЦ: ввод диапазона для ИЗВЛЕЧЕНИЯ =====
    if mode == "pages_extract_wait_pages":
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await message.answer(t(user_id, "pages_no_pdf_editor"))
            user_modes[user_id] = "compress"
            return

        if text_val == "all":
            pages = list(range(1, num_pages + 1))
        else:
            pages = parse_page_range(text_raw, num_pages)

        if not pages:
            await message.answer(t(user_id, "pages_extract_range_failed"))
            return

        try:
            reader = PdfReader(str(pdf_path))
        except Exception as e:
            logger.error(f"Pages extract open error: {e}")
            await message.answer(t(user_id, "pages_open_error"))
            return

        writer = PdfWriter()
        for p in pages:
            writer.add_page(reader.pages[p - 1])

        safe_suffix = text_raw.replace(",", "_").replace("-", "_").replace(" ", "")
        out_path = FILES_DIR / f"{Path(pdf_path).stem}_extract_{safe_suffix}.pdf"
        try:
            with open(out_path, "wb") as f:
                writer.write(f)
        except Exception as e:
            logger.error(f"Pages extract write error: {e}")
            await message.answer(t(user_id, "pages_save_error"))
            return

        await message.answer_document(
            types.FSInputFile(out_path),
            caption=t(user_id, "pages_extract_done", raw=text_raw),
        )

        user_modes[user_id] = "pages_menu"
        await message.answer(
            t(user_id, "pages_continue_source_edit"),
            reply_markup=get_pages_menu_keyboard(user_id),
        )
        return

    # ===== ВОДЯНОЙ ЗНАК: шаг 2 — текст =====
    if mode == "watermark_wait_text":
        state = user_watermark_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")

        if not pdf_path or not Path(pdf_path).exists():
            await message.answer(t(user_id, "wm_no_pdf"))
            user_modes[user_id] = "watermark"
            user_watermark_state[user_id] = {}
            return

        wm_text = (message.text or "").strip()
        if not wm_text:
            await message.answer(t(user_id, "wm_empty_text"))
            return

        state["text"] = wm_text
        state["pos"] = "11"
        state["mosaic"] = False
        user_watermark_state[user_id] = state
        user_modes[user_id] = "watermark_wait_style"

        await message.answer(
            t(user_id, "wm_choose_pos_full"),
            reply_markup=get_watermark_keyboard(user_id, pos="11", mosaic=False),
        )
        return

    # ===== ВОДЯНОЙ ЗНАК: напоминание =====
    if mode == "watermark_wait_style":
        await message.answer(t(user_id, "wm_style_reminder"))
        return

    # ===== MERGE: "Готово" / "done" =====
    if mode == "merge" and text_val in ("готово", "done", "/done", "/merge"):
        files_list = user_merge_files.get(user_id, [])

        if len(files_list) < 2:
            await message.answer(t(user_id, "merge_need_two"))
            return

        await message.answer(
            t(user_id, "merge_start", count=len(files_list))
        )

        merged_name = Path(files_list[0]).stem + "_merged.pdf"
        merged_path = FILES_DIR / merged_name

        try:
            merger = PdfMerger()
            for p in files_list:
                merger.append(str(p))
            merger.write(str(merged_path))
            merger.close()
        except Exception as e:
            logger.error(e)
            await message.answer(t(user_id, "merge_error"))
            return

        await message.answer_document(
            types.FSInputFile(merged_path),
            caption=t(user_id, "msg_done"),
        )
        user_merge_files[user_id] = []
        return

    # любые другие текстовые сообщения здесь не обрабатываем
    return

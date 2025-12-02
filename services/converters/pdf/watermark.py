# handlers/watermark.py
from pathlib import Path

from aiogram import Router, types, F

from settings import logger
from state import user_modes, user_watermark_state
from keyboards import get_watermark_keyboard
from i18n import t
from utils import ensure_pro  # <-- добавляем импорт

router = Router()


@router.callback_query(F.data.startswith("wm_pos:"))
async def wm_pos_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = user_watermark_state.setdefault(user_id, {})
    pos_code = callback.data.split(":", 1)[1]
    state["pos"] = pos_code
    user_watermark_state[user_id] = state

    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_watermark_keyboard(
                user_id=user_id,
                pos=pos_code,
                mosaic=state.get("mosaic", False),
            )
        )
    except Exception as e:
        logger.error(f"wm_pos edit_reply_markup error: {e}")

    await callback.answer()


@router.callback_query(F.data == "wm_toggle_mosaic")
async def wm_mosaic_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = user_watermark_state.setdefault(user_id, {})
    state["mosaic"] = not state.get("mosaic", False)

    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_watermark_keyboard(
                user_id=user_id,
                pos=state.get("pos", "11"),
                mosaic=state["mosaic"],
            )
        )
    except Exception as e:
        logger.error(f"wm_toggle_mosaic edit_reply_markup error: {e}")

    await callback.answer()


@router.callback_query(F.data == "wm_apply")
async def wm_apply_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    # ---------- ПРОВЕРКА PRO ----------
    # если PRO нет — показываем сообщение и выходим из хендлера
    if not await ensure_pro(callback.message):
        await callback.answer()  # закрыть "часики" на кнопке
        return
    # ----------------------------------

    state = user_watermark_state.get(user_id) or {}
    pdf_path = state.get("pdf_path")
    wm_text = state.get("text")
    pos = state.get("pos", "11")
    mosaic = state.get("mosaic", False)

    if not pdf_path or not Path(pdf_path).exists() or not wm_text:
        await callback.answer(
            t(user_id, "wm_no_data"),
            show_alert=True,
        )
        user_modes[user_id] = "watermark"
        user_watermark_state[user_id] = {}
        return

    await callback.answer()
    try:
        await callback.message.edit_text(t(user_id, "wm_applying"))
    except Exception:
        pass

    out_path = apply_watermark(Path(pdf_path), wm_text, pos, mosaic)

    if not out_path or not out_path.exists():
        await callback.message.answer(t(user_id, "wm_save_failed"))
        return

    await callback.message.answer_document(
        types.FSInputFile(out_path),
        caption=t(user_id, "wm_done"),
    )

    user_watermark_state[user_id] = {}
    user_modes[user_id] = "compress"
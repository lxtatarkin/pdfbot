# handlers/pro.py
import os
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)

from i18n import t, get_user_lang
from settings import (
    is_pro,
    format_mb,
    PRO_MAX_SIZE,
    get_pro_expire_ts,
    extend_pro,
)
from legal import TERMS_URL, PRIVACY_URL

router = Router()

# Конфиг планов: дни + env для Stars
PLAN_CONFIG = {
    "month": {
        "days": 30,
        "env": "PRO_PRICE_MONTH_STARS",
        "default": 150,
    },
    "quarter": {
        "days": 90,
        "env": "PRO_PRICE_QUARTER_STARS",
        "default": 300,
    },
    "year": {
        "days": 365,
        "env": "PRO_PRICE_YEAR_STARS",
        "default": 900,
    },
}


def get_price_stars(plan: str) -> int:
    cfg = PLAN_CONFIG[plan]
    return int(os.getenv(cfg["env"], str(cfg["default"])))


def format_date(ts: int, lang: str) -> str:
    dt = datetime.fromtimestamp(ts, timezone.utc)
    if lang == "ru":
        return dt.strftime("%d.%m.%Y")
    return dt.strftime("%Y-%m-%d")


def build_pro_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """
    Кнопки подписки берём из i18n:
    pro_btn_month / pro_btn_quarter / pro_btn_year
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_month"),
                    callback_data="buy:month",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_quarter"),
                    callback_data="buy:quarter",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(user_id, "pro_btn_year"),
                    callback_data="buy:year",
                )
            ],
        ]
    )


@router.message(Command("pro"))
async def cmd_pro(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    # Статус подписки (динамическая часть)
    expires_ts = get_pro_expire_ts(user_id)
    if expires_ts:
        until_str = format_date(expires_ts, lang)
        if lang == "ru":
            status = f"У тебя уже активен PRO до <b>{until_str}</b>."
        else:
            status = f"Your PRO is active until <b>{until_str}</b>."
    else:
        if lang == "ru":
            status = "У тебя пока нет PRO-подписки."
        else:
            status = "You don't have a PRO subscription yet."

    # Описание и юридический текст — из i18n
    body = t(
        user_id,
        "pro_info",
        terms=TERMS_URL,
        privacy=PRIVACY_URL,
    )

    await message.answer(
        status + "\n\n" + body,
        reply_markup=build_pro_keyboard(user_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("buy:"))
async def buy_callback(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    lang = get_user_lang(user_id)

    plan = call.data.split(":", 1)[1]  # month / quarter / year
    if plan not in PLAN_CONFIG:
        await call.answer("Unknown plan", show_alert=True)
        return

    price_stars = get_price_stars(plan)

    # Заголовок и описание инвойса делаем короткими и завязанными на язык
    title = "PDF Converter Bot PRO"

    if lang == "ru":
        if plan == "month":
            desc_period = "на 1 месяц"
        elif plan == "quarter":
            desc_period = "на 3 месяца"
        else:
            desc_period = "на 12 месяцев"

        description = (
            f"Подписка PRO {desc_period}. "
            f"Лимит до {format_mb(PRO_MAX_SIZE)}, все функции без ограничений."
        )
    else:
        if plan == "month":
            desc_period = "for 1 month"
        elif plan == "quarter":
            desc_period = "for 3 months"
        else:
            desc_period = "for 12 months"

        description = (
            f"PRO subscription {desc_period}. "
            f"Limit up to {format_mb(PRO_MAX_SIZE)}, all features unlocked."
        )

    prices = [LabeledPrice(label=title, amount=price_stars)]

    await bot.send_invoice(
        chat_id=call.message.chat.id,
        title=title,
        description=description[:255],
        payload=f"pro:{plan}",
        provider_token="",  # пусто для Stars
        currency="XTR",
        prices=prices,
    )

    await call.answer()  # закрыть "loading" на кнопке


@router.pre_checkout_query()
async def process_pre_checkout_query(query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    payload = message.successful_payment.invoice_payload or ""
    parts = payload.split(":")
    plan = parts[1] if len(parts) > 1 else "month"
    if plan not in PLAN_CONFIG:
        plan = "month"

    days = PLAN_CONFIG[plan]["days"]
    new_exp = extend_pro(user_id, days)
    until_str = format_date(new_exp, lang)

    base_text = t(
        user_id,
        "pro_activated",
        max_size=format_mb(PRO_MAX_SIZE),
    )

    if lang == "ru":
        extra = f"\n\nПодписка действует до <b>{until_str}</b>."
    else:
        extra = f"\n\nSubscription is valid until <b>{until_str}</b>."

    await message.answer(base_text + extra, parse_mode="HTML")
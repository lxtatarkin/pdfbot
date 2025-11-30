# handlers/pro.py
import os

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice

from i18n import t, get_user_lang
from settings import is_pro, add_pro_user, format_mb, PRO_MAX_SIZE
from legal import TERMS_URL, PRIVACY_URL

router = Router()

# Цена в Stars: читаем из переменной окружения, по умолчанию 300 Stars
PRO_PRICE_STARS = int(os.getenv("PRO_PRICE_STARS", "300"))

PRICE = [
    LabeledPrice(
        label="PDF Tools PRO",
        amount=PRO_PRICE_STARS,  # в Stars единицы == 1 Star
    )
]


@router.message(Command("pro"))
async def cmd_pro(message: Message, bot: Bot):
    user_id = message.from_user.id
    lang_code = get_user_lang(user_id)

    # Уже PRO — просто текст
    if is_pro(user_id):
        await message.answer(
            t(
                user_id,
                "pro_already",
                max_size=format_mb(PRO_MAX_SIZE),
                terms=TERMS_URL,
                privacy=PRIVACY_URL,
            ),
            parse_mode="HTML",
        )
        return

    # Текст для инвойса (минимальный, без i18n-ключей, чтобы не упираться в длину)
    if lang_code == "ru":
        title = "PDF Tools PRO"
        description = (
            f"Подписка PRO для PDF Tools. "
            f"Лимит до {format_mb(PRO_MAX_SIZE)}, без ограничений по функциям."
        )
    else:
        title = "PDF Tools PRO"
        description = (
            f"PRO subscription for PDF Tools. "
            f"Limit up to {format_mb(PRO_MAX_SIZE)}, all features unlocked."
        )

    await bot.send_invoice(
        chat_id=message.chat.id,
        title=title,
        description=description[:255],
        payload=f"pro-{user_id}",  # полезная нагрузка для себя
        provider_token="",  # ОБЯЗАТЕЛЬНО пустая строка для Telegram Stars
        currency="XTR",  # валюта Stars
        prices=PRICE,
        # Для простоты делаем разовый платеж «вечный PRO».
        # Если захочешь подписку — добавим subscription_period=2592000.
    )


# Обязательный шаг: подтвердить pre_checkout_query
@router.pre_checkout_query()
async def process_pre_checkout_query(
    query: PreCheckoutQuery,
    bot: Bot,
):
    await bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)


# Успешная оплата — помечаем пользователя как PRO
@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    user_id = message.from_user.id
    add_pro_user(user_id)

    await message.answer(
        t(
            user_id,
            "pro_activated",
            max_size=format_mb(PRO_MAX_SIZE),
            terms=TERMS_URL,
            privacy=PRIVACY_URL,
        ),
        parse_mode="HTML",
    )
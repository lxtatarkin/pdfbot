import os
import json
from pathlib import Path
from typing import Dict

import stripe
from flask import Flask, request, redirect, abort

# ===== Stripe config =====
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRICE_ID = os.getenv("STRIPE_PRICE_ID")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# ===== Flask app =====
app = Flask(__name__)

PRO_USERS_FILE = Path("pro_users.json")

# ===== i18n =====
MESSAGES: Dict[str, Dict[str, str]] = {
    "ru": {
        "success": "Оплата прошла успешно. Можешь вернуться в Telegram-бот.",
        "cancel": "Оплата отменена. Можешь попробовать ещё раз из бота.",
        "missing_user": "Отсутствует параметр user_id.",
        "error_creating_session": "Ошибка при создании сессии оплаты.",
    },
    "en": {
        "success": "Payment successful. You can now return to the Telegram bot.",
        "cancel": "Payment was canceled. You can try again from the bot.",
        "missing_user": "Missing user_id parameter.",
        "error_creating_session": "Error while creating checkout session.",
    },
}


def normalize_lang(lang_raw: str | None) -> str:
    if not lang_raw:
        return "ru"
    lang_raw = lang_raw.lower()
    if lang_raw.startswith("en"):
        return "en"
    if lang_raw.startswith("ru"):
        return "ru"
    # при желании можно добавить другие, пока мапим всё неизвестное в en/ru
    return "en"


def t(key: str, lang: str) -> str:
    return MESSAGES.get(lang, MESSAGES["ru"]).get(key, key)


# ===== PRO users storage (простой JSON для staging) =====
def add_pro_user(user_id: int) -> None:
    data: list[int] = []
    if PRO_USERS_FILE.exists():
        try:
            data = json.loads(PRO_USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = []
    if user_id not in data:
        data.append(user_id)
        PRO_USERS_FILE.write_text(json.dumps(data), encoding="utf-8")


# ===== Routes =====
@app.get("/buy-pro")
def buy_pro():
    tg_user_id = request.args.get("user_id")
    lang = normalize_lang(request.args.get("lang"))

    if not tg_user_id:
        return t("missing_user", lang), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",  # или "payment" для разовой оплаты
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            success_url=f"{APP_BASE_URL}/payment-success?lang={lang}",
            cancel_url=f"{APP_BASE_URL}/payment-cancel?lang={lang}",
            metadata={"tg_user_id": tg_user_id, "lang": lang},
        )
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return t("error_creating_session", lang), 500

    return redirect(checkout_session.url, code=303)


@app.post("/stripe/webhook")
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=WEBHOOK_SECRET,
        )
    except Exception as e:
        print("Webhook error:", e)
        return abort(400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {}) or {}
        tg_user_id = metadata.get("tg_user_id")
        lang = normalize_lang(metadata.get("lang"))

        if tg_user_id:
            try:
                add_pro_user(int(tg_user_id))
            except ValueError:
                print(f"Invalid tg_user_id in metadata: {tg_user_id}")
            else:
                print(f"Activated PRO for user {tg_user_id} ({lang})")

    return "", 200


@app.get("/payment-success")
def payment_success():
    lang = normalize_lang(request.args.get("lang"))
    return t("success", lang)


@app.get("/payment-cancel")
def payment_cancel():
    lang = normalize_lang(request.args.get("lang"))
    return t("cancel", lang)


@app.get("/health")
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

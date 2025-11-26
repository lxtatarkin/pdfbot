import os
import json
from pathlib import Path
from typing import Dict

import stripe
from flask import Flask, request, redirect, abort, jsonify

# ===== Stripe config =====
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
DEFAULT_PRICE_ID = os.getenv("STRIPE_PRICE_ID")  # опционально
PRICE_MONTH = os.getenv("STRIPE_PRICE_ID_MONTH")
PRICE_QUARTER = os.getenv("STRIPE_PRICE_ID_QUARTER")
PRICE_YEAR = os.getenv("STRIPE_PRICE_ID_YEAR")

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

app = Flask(__name__)
PRO_USERS_FILE = Path("pro_users.json")

# локализация для HTML-страниц
MESSAGES: Dict[str, Dict[str, str]] = {
    "ru": {
        "success": "Оплата прошла успешно. Можешь вернуться в Telegram-бот.",
        "success_btn": "Открыть Telegram",
        "cancel": "Оплата отменена. Можешь попробовать ещё раз из бота.",
        "missing_user": "Отсутствует параметр user_id.",
        "error_creating_session": "Ошибка при создании сессии оплаты.",
    },
    "en": {
        "success": "Payment successful. You can now return to the Telegram bot.",
        "success_btn": "Open Telegram",
        "cancel": "Payment was canceled. You can try again from the bot.",
        "missing_user": "Missing user_id parameter.",
        "error_creating_session": "Error while creating checkout session.",
    },
}


def normalize_lang(raw: str | None) -> str:
    if not raw:
        return "en"
    code = raw.lower()
    if code.startswith(("ru", "uk", "be")):
        return "ru"
    return "en"


def t_local(key: str, lang: str) -> str:
    return MESSAGES.get(lang, MESSAGES["en"]).get(key, key)


def choose_price_id(raw: str | None) -> str:
    """
    Берём price_id из query (?price_id=...), если его нет —
    отдаём MONTH или DEFAULT_PRICE_ID.
    """
    if raw:
        return raw

    if PRICE_MONTH:
        return PRICE_MONTH

    if DEFAULT_PRICE_ID:
        return DEFAULT_PRICE_ID

    # на крайний случай — чтобы не упасть
    return PRICE_MONTH or PRICE_QUARTER or PRICE_YEAR


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


@app.get("/buy-pro")
def buy_pro():
    tg_user_id = request.args.get("user_id")
    price_id = choose_price_id(request.args.get("price_id"))
    lang = normalize_lang(request.args.get("lang"))  # на будущее, если захочешь добавлять

    if not tg_user_id:
        return t_local("missing_user", lang), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{APP_BASE_URL}/payment-success?lang={lang}",
            cancel_url=f"{APP_BASE_URL}/payment-cancel?lang={lang}",
            metadata={"tg_user_id": tg_user_id, "lang": lang, "price_id": price_id},
        )
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return t_local("error_creating_session", lang), 500

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
        price_id = metadata.get("price_id")
        print(f"Checkout completed: user={tg_user_id}, price_id={price_id}, lang={lang}")

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

    bot_username = os.getenv("BOT_USERNAME", "your_bot_username")  # заменишь на своего
    telegram_link = f"https://t.me/{bot_username}?start=pro_ok"

    msg = t_local("success", lang)
    btn_text = t_local("success_btn", lang)

    return f"""
    <html>
      <head>
        <meta charset="utf-8">
        <title>Success</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <style>
          body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            padding: 32px;
            text-align: center;
            background-color: #f5f5f5;
          }}
          .card {{
            max-width: 420px;
            margin: 40px auto;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            padding: 32px 24px;
          }}
          h2 {{
            margin-top: 0;
            margin-bottom: 16px;
            font-size: 22px;
          }}
          p {{
            margin: 0 0 24px 0;
            font-size: 15px;
            color: #444444;
          }}
          a.button {{
            display: inline-block;
            padding: 12px 24px;
            background: #4CAF50;
            color: #ffffff;
            text-decoration: none;
            border-radius: 999px;
            font-size: 16px;
            font-weight: 600;
          }}
        </style>
      </head>
      <body>
        <div class="card">
          <h2>✅ {msg}</h2>
          <p>{"" if lang == "en" else ""}</p>
          <a class="button" href="{telegram_link}">{btn_text}</a>
        </div>
      </body>
    </html>
    """


@app.get("/payment-cancel")
def payment_cancel():
    lang = normalize_lang(request.args.get("lang"))
    return t_local("cancel", lang)


@app.get("/is-pro")
def is_pro():
    """
    Вспомогательный эндпоинт для бота.
    GET /is-pro?user_id=123 -> {"pro": true/false}
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"pro": False, "error": "missing user_id"}), 400

    try:
        uid = int(user_id)
    except ValueError:
        return jsonify({"pro": False, "error": "bad user_id"}), 400

    data: list[int] = []
    if PRO_USERS_FILE.exists():
        try:
            data = json.loads(PRO_USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = []

    return jsonify({"pro": uid in data}), 200


@app.get("/health")
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
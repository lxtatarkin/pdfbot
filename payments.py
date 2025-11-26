import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

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
CUSTOMERS_FILE = Path("customers.json")  # связь tg_user_id <-> stripe_customer_id

# локализация для HTML-страниц
MESSAGES: Dict[str, Dict[str, str]] = {
    "ru": {
        "success": "Оплата прошла успешно. Можешь вернуться в Telegram-бот.",
        "success_btn": "Открыть Telegram",
        "cancel": "Оплата отменена. Можешь попробовать ещё раз из бота.",
        "missing_user": "Отсутствует параметр user_id.",
        "error_creating_session": "Ошибка при создании сессии оплаты.",
        "no_customer": "Не найдена активная подписка для этого пользователя.",
        "portal_error": "Не удалось открыть страницу управления подпиской. Попробуйте позже.",
    },
    "en": {
        "success": "Payment successful. You can now return to the Telegram bot.",
        "success_btn": "Open Telegram",
        "cancel": "Payment was canceled. You can try again from the bot.",
        "missing_user": "Missing user_id parameter.",
        "error_creating_session": "Error while creating checkout session.",
        "no_customer": "No active subscription found for this user.",
        "portal_error": "Failed to open subscription management page. Please try again later.",
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


# ==========================
#   PRO USERS STORAGE
# ==========================


def add_pro_user(user_id: int) -> None:
    data: List[int] = []
    if PRO_USERS_FILE.exists():
        try:
            data = json.loads(PRO_USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = []
    if user_id not in data:
        data.append(user_id)
        PRO_USERS_FILE.write_text(json.dumps(data), encoding="utf-8")


def remove_pro_user(user_id: int) -> None:
    if not PRO_USERS_FILE.exists():
        return
    try:
        data: List[int] = json.loads(PRO_USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    new_data = [uid for uid in data if uid != user_id]
    PRO_USERS_FILE.write_text(json.dumps(new_data), encoding="utf-8")


# ==========================
#   CUSTOMERS STORAGE
#   customers.json: [{"user_id": 123, "customer_id": "cus_XXX"}, ...]
# ==========================


def _load_customers() -> List[Dict[str, Any]]:
    if not CUSTOMERS_FILE.exists():
        return []
    try:
        data = json.loads(CUSTOMERS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_customers(customers: List[Dict[str, Any]]) -> None:
    CUSTOMERS_FILE.write_text(
        json.dumps(customers, ensure_ascii=False),
        encoding="utf-8",
    )


def upsert_customer(user_id: int, customer_id: str) -> None:
    customers = _load_customers()
    found = False
    for c in customers:
        if int(c.get("user_id", 0)) == user_id:
            c["customer_id"] = customer_id
            found = True
            break
    if not found:
        customers.append({"user_id": user_id, "customer_id": customer_id})
    _save_customers(customers)


def find_customer_by_user_id(user_id: int) -> Optional[str]:
    customers = _load_customers()
    for c in customers:
        try:
            if int(c.get("user_id", 0)) == user_id:
                return str(c.get("customer_id"))
        except Exception:
            continue
    return None


def find_user_by_customer_id(customer_id: str) -> Optional[int]:
    customers = _load_customers()
    for c in customers:
        if str(c.get("customer_id")) == customer_id:
            try:
                return int(c.get("user_id"))
            except Exception:
                return None
    return None


# ==========================
#   ROUTES
# ==========================


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

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    # Успешное завершение Checkout-сессии (первая покупка)
    if event_type == "checkout.session.completed":
        session = data_object
        metadata = session.get("metadata", {}) or {}
        tg_user_id = metadata.get("tg_user_id")
        lang = normalize_lang(metadata.get("lang"))
        price_id = metadata.get("price_id")
        customer_id = session.get("customer")
        print(
            f"Checkout completed: user={tg_user_id}, price_id={price_id}, "
            f"lang={lang}, customer_id={customer_id}"
        )

        if tg_user_id:
            try:
                uid = int(tg_user_id)
            except ValueError:
                print(f"Invalid tg_user_id in metadata: {tg_user_id}")
            else:
                add_pro_user(uid)
                if customer_id:
                    upsert_customer(uid, customer_id)
                print(f"Activated PRO for user {uid} ({lang})")

    # Подписка отменена (через портал/Stripe)
    elif event_type == "customer.subscription.deleted":
        subscription = data_object
        customer_id = subscription.get("customer")
        print(f"Subscription deleted for customer={customer_id}")
        if customer_id:
            user_id = find_user_by_customer_id(customer_id)
            if user_id is not None:
                remove_pro_user(user_id)
                print(f"Deactivated PRO for user {user_id} (subscription deleted)")

    return "", 200


@app.get("/payment-success")
def payment_success():
    lang = normalize_lang(request.args.get("lang"))

    bot_username = os.getenv("BOT_USERNAME", "your_bot_username")  # ЗАМЕНИ на своего
    tg_deeplink = f"tg://resolve?domain={bot_username}&start=pro_ok"
    tg_web_link = f"https://t.me/{bot_username}?start=pro_ok"

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
            margin: 0 0 16px 0;
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
            margin-bottom: 12px;
          }}
          a.small {{
            font-size: 13px;
            color: #555555;
          }}
        </style>
      </head>
      <body>
        <div class="card">
          <h2>✅ {msg}</h2>
          <p></p>
          <a class="button" href="{tg_deeplink}">{btn_text}</a>
          <br/>
          <a class="small" href="{tg_web_link}">Если кнопка не сработала — открыть Telegram по ссылке</a>
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

    data: List[int] = []
    if PRO_USERS_FILE.exists():
        try:
            data = json.loads(PRO_USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = []

    return jsonify({"pro": uid in data}), 200


@app.get("/customer-portal")
def customer_portal():
    """
    Открытие Stripe Customer Portal для управления подпиской:
    GET /customer-portal?user_id=123&lang=ru
    """
    raw_user_id = request.args.get("user_id")
    lang = normalize_lang(request.args.get("lang"))

    if not raw_user_id:
        return t_local("missing_user", lang), 400

    try:
        user_id = int(raw_user_id)
    except ValueError:
        return t_local("missing_user", lang), 400

    customer_id = find_customer_by_user_id(user_id)
    if not customer_id:
        return t_local("no_customer", lang), 404

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{APP_BASE_URL}/payment-success?lang={lang}",
        )
    except Exception as e:
        print(f"Error creating billing portal session: {e}")
        return t_local("portal_error", lang), 500

    return redirect(portal_session.url, code=303)


@app.get("/health")
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
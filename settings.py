# settings.py
import os
import logging
from typing import Optional

import requests

# ===== Logging =====
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ===== Bot config =====
TOKEN = os.getenv("BOT_TOKEN")              # важно!
BOT_USERNAME = os.getenv("BOT_USERNAME")    # нужно для deeplink

# ===== Limits =====
FREE_MAX_SIZE = 20 * 1024 * 1024     # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024     # 100 MB

def format_mb(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    return f"{int(mb)} MB"

# ===== Billing service settings =====
# В pdfbot-staging обязательно должно быть:
# BILLING_BASE_URL=https://pdfbot-billing-production.up.railway.app
BILLING_BASE_URL = os.getenv("BILLING_BASE_URL")

# ===== PRO CHECK =====

def _is_pro_remote(user_id: int) -> Optional[bool]:
    """
    Делает запрос GET /is-pro?user_id=...
    Возвращает True/False, либо None при ошибке.
    """
    if not BILLING_BASE_URL:
        logger.error("BILLING_BASE_URL not set")
        return None

    url = f"{BILLING_BASE_URL.rstrip('/')}/is-pro"

    try:
        resp = requests.get(url, params={"user_id": user_id}, timeout=3)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Billing is_pro(%s) -> %s", user_id, data)
        return bool(data.get("pro"))
    except Exception as e:
        logger.error("Error calling billing: %s", e)
        return None


def is_pro(user_id: int) -> bool:
    """
    Единственный источник истины: billing-сервис.
    """
    result = _is_pro_remote(user_id)
    return bool(result)


def get_user_limit(user_id: int) -> int:
    """
    Лимит зависит от тарифа.
    """
    return PRO_MAX_SIZE if is_pro(user_id) else FREE_MAX_SIZE
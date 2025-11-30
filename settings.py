import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# ========== LOGGING ==========
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ========== PATHS ==========
BASE_DIR = Path(__file__).resolve().parent

FILES_DIR = BASE_DIR / "files"
TMP_DIR = BASE_DIR / "tmp"

FILES_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# ========== BOT CONFIG ==========
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN is not set in environment")

BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")

# ========== LIMITS ==========
FREE_MAX_SIZE = 20 * 1024 * 1024  # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024  # 100 MB


def format_mb(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    return f"{int(mb)} MB"


# ========== PRO SUBSCRIPTIONS (срок действия) ==========

PRO_USERS_FILE = BASE_DIR / "pro_users.json"


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _load_subscriptions() -> List[Dict[str, Any]]:
    """
    Формат файла:
    [
      {"user_id": 123, "expires_at": 1735689600},
      ...
    ]

    Для совместимости со старым форматом [123, 456]:
    считаем, что это «вечный PRO» до 2100-01-01.
    """
    if not PRO_USERS_FILE.exists():
        return []

    try:
        data = json.loads(PRO_USERS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Error reading pro_users.json: %s", e)
        return []

    result: List[Dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, int):
                result.append(
                    {
                        "user_id": int(item),
                        "expires_at": 4102444800,  # 2100-01-01
                    }
                )
            elif isinstance(item, dict):
                try:
                    uid = int(item.get("user_id"))
                    exp = int(item.get("expires_at"))
                    result.append({"user_id": uid, "expires_at": exp})
                except Exception:
                    continue

    return result


def _save_subscriptions(subs: List[Dict[str, Any]]) -> None:
    try:
        PRO_USERS_FILE.write_text(
            json.dumps(subs, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error("Error writing pro_users.json: %s", e)


def get_pro_expire_ts(user_id: int) -> Optional[int]:
    """
    Возвращает timestamp окончания PRO или None, если нет активной подписки.
    """
    now = _now_ts()
    for sub in _load_subscriptions():
        try:
            if int(sub["user_id"]) == user_id and int(sub["expires_at"]) > now:
                return int(sub["expires_at"])
        except Exception:
            continue
    return None


def extend_pro(user_id: int, days: int) -> int:
    """
    Продлевает/выдаёт PRO на указанное число дней.
    Возвращает новый expires_at (timestamp).
    """
    now = _now_ts()
    subs = _load_subscriptions()

    current_exp: Optional[int] = None
    for sub in subs:
        try:
            if int(sub["user_id"]) == user_id:
                cur = int(sub["expires_at"])
                if current_exp is None or cur > current_exp:
                    current_exp = cur
        except Exception:
            continue

    base = current_exp if current_exp and current_exp > now else now
    new_exp = base + days * 86400

    updated = False
    for sub in subs:
        try:
            if int(sub["user_id"]) == user_id:
                sub["expires_at"] = new_exp
                updated = True
        except Exception:
            continue

    if not updated:
        subs.append({"user_id": user_id, "expires_at": new_exp})

    _save_subscriptions(subs)
    logger.info(
        "PRO extended for user %s until %s",
        user_id,
        datetime.fromtimestamp(new_exp, timezone.utc),
    )
    return new_exp


def is_pro(user_id: int) -> bool:
    """
    Пользователь PRO, если срок подписки ещё не истёк.
    """
    return get_pro_expire_ts(user_id) is not None


def get_user_limit(user_id: int) -> int:
    """
    Возвращает лимит по тарифу.
    """
    return PRO_MAX_SIZE if is_pro(user_id) else FREE_MAX_SIZE
import os
import json
import logging
from typing import Optional, Set
from pathlib import Path

# ========== LOGGING ==========
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ========== PATHS ==========
BASE_DIR = Path(__file__).resolve().parent

# Папка для файлов, с которыми работает бот
FILES_DIR = BASE_DIR / "files"
TMP_DIR = BASE_DIR / "tmp"

FILES_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# ========== BOT CONFIG ==========
# Токен бота из переменной окружения BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN is not set in environment")

# username бота без @ — нужен для deeplink и пр.
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")

# ========== LIMITS ==========
FREE_MAX_SIZE = 20 * 1024 * 1024  # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024  # 100 MB


def format_mb(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    return f"{int(mb)} MB"


# ========== PRO USERS STORAGE (локально, без Stripe) ==========

PRO_USERS_FILE = BASE_DIR / "pro_users.json"


def _load_pro_users() -> Set[int]:
    if not PRO_USERS_FILE.exists():
        return set()
    try:
        data = json.loads(PRO_USERS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {int(x) for x in data}
    except Exception as e:
        logger.error("Error reading pro_users.json: %s", e)
    return set()


def _save_pro_users(users: Set[int]) -> None:
    try:
        PRO_USERS_FILE.write_text(
            json.dumps(sorted(users), ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error("Error writing pro_users.json: %s", e)


def add_pro_user(user_id: int) -> None:
    users = _load_pro_users()
    if user_id not in users:
        users.add(user_id)
        _save_pro_users(users)
        logger.info("PRO activated for user %s", user_id)


def remove_pro_user(user_id: int) -> None:
    users = _load_pro_users()
    if user_id in users:
        users.remove(user_id)
        _save_pro_users(users)
        logger.info("PRO deactivated for user %s", user_id)


def is_pro(user_id: int) -> bool:
    """
    Истина — если пользователь есть в локальном списке PRO.
    """
    users = _load_pro_users()
    return user_id in users


def get_user_limit(user_id: int) -> int:
    """
    Возвращает лимит по тарифу.
    """
    return PRO_MAX_SIZE if is_pro(user_id) else FREE_MAX_SIZE
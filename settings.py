# settings.py
import os
import logging
from pathlib import Path

from dotenv import load_dotenv

# =========================
#   LOAD ENV
# =========================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ===== PRO / FREE SETTINGS =====
PRO_USERS_RAW = os.getenv("PRO_USERS", "")  # comma-separated user IDs

PRO_USERS: set[int] = set()
for part in PRO_USERS_RAW.split(","):
    part = part.strip()
    if part.isdigit():
        PRO_USERS.add(int(part))

FREE_MAX_SIZE = 20 * 1024 * 1024      # 20 MB
PRO_MAX_SIZE = 100 * 1024 * 1024      # 100 MB


def is_pro(user_id: int) -> bool:
    return user_id in PRO_USERS


def get_user_limit(user_id: int) -> int:
    return PRO_MAX_SIZE if is_pro(user_id) else FREE_MAX_SIZE


def format_mb(bytes_size: int) -> str:
    return f"{bytes_size / (1024 * 1024):.0f} МБ"


# =========================
#   LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("pdfbot")

# =========================
#   FILE STORAGE
# =========================
BASE_DIR = Path(__file__).resolve().parent
FILES_DIR = BASE_DIR / "files"
FILES_DIR.mkdir(exist_ok=True)
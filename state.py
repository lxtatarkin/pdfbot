from pathlib import Path
from typing import Dict, List

import json
import os
import requests

# mode:
#   compress, pdf_text, doc_photo, merge, split, ocr, searchable_pdf,
#   watermark, watermark_wait_text, watermark_wait_style,
#   pages_wait_pdf, pages_menu,
#   pages_rotate_wait_pages, pages_rotate_wait_angle,
#   pages_delete_wait_pages, pages_extract_wait_pages
user_modes: Dict[int, str] = {}

# список PDF-файлов для объединения
user_merge_files: Dict[int, List[Path]] = {}

# состояние для водяных знаков:
# user_id -> {"pdf_path": Path, "text": str, "pos": "11", "mosaic": bool}
user_watermark_state: Dict[int, dict] = {}

# состояние для редактора страниц:
# user_id -> {"pdf_path": Path, "pages": int, ... }
user_pages_state: Dict[int, dict] = {}

# ==========================
#   PRO USERS (через billing)
# ==========================

BILLING_BASE_URL = os.getenv(
    "BILLING_BASE_URL",
    "https://pdfbot-billing-production.up.railway.app",
)


def is_pro_user(user_id: int) -> bool:
    """
    Проверяет PRO-статус пользователя через сервис billing.
    Делает запрос:
        GET {BILLING_BASE_URL}/is-pro?user_id=...
    """
    try:
        resp = requests.get(
            f"{BILLING_BASE_URL}/is-pro",
            params={"user_id": user_id},
            timeout=3,
        )
        if resp.status_code != 200:
            return False

        data = resp.json()
        return bool(data.get("pro"))
    except Exception as e:
        # можно залогировать e, если нужно
        return False
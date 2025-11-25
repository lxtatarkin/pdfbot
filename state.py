from pathlib import Path

# mode:
#   compress, pdf_text, doc_photo, merge, split, ocr, searchable_pdf,
#   watermark, watermark_wait_text, watermark_wait_style,
#   pages_wait_pdf, pages_menu,
#   pages_rotate_wait_pages, pages_rotate_wait_angle,
#   pages_delete_wait_pages, pages_extract_wait_pages
user_modes: dict[int, str] = {}

# список PDF-файлов для объединения
user_merge_files: dict[int, list[Path]] = {}

# состояние для водяных знаков:
# user_id -> {"pdf_path": Path, "text": str, "pos": "11", "mosaic": bool}
user_watermark_state: dict[int, dict] = {}

# состояние для редактора страниц:
# user_id -> {"pdf_path": Path, "pages": int, ... }
user_pages_state: dict[int, dict] = {}

# ==========================
#   PRO USERS STORAGE
# ==========================

import json

PRO_USERS_FILE = Path("pro_users.json")


def _load_pro_users() -> set[int]:
    if PRO_USERS_FILE.exists():
        try:
            data = json.loads(PRO_USERS_FILE.read_text(encoding="utf-8"))
            return set(map(int, data))
        except Exception:
            return set()
    return set()


def _save_pro_users(users: set[int]):
    PRO_USERS_FILE.write_text(
        json.dumps(list(users), ensure_ascii=False),
        encoding="utf-8"
    )


def is_pro_user(user_id: int) -> bool:
    """Проверяет, есть ли пользователь в списке PRO."""
    users = _load_pro_users()
    return user_id in users


def add_pro_user(user_id: int):
    """Добавляет PRO-пользователя (Stripe webhook вызывает эту функцию)."""
    users = _load_pro_users()
    users.add(int(user_id))
    _save_pro_users(users)

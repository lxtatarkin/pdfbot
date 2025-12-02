# state.py
from pathlib import Path
from typing import Dict, List

import json
import os

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

# Если у тебя здесь были переменные/логика, связанные с billing API
# (BILLING_BASE_URL, is_pro_user и т.п.) — их нужно удалить,
# потому что теперь единственный источник правды по подписке — PostgreSQL
# и функции is_pro/get_user_limit из settings.py.
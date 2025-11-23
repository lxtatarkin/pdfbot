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

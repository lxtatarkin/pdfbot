# pdf_services.py — совместимость/фасад
from services.converters.image_to_pdf import image_file_to_pdf
from services.converters.office_to_pdf import office_doc_to_pdf
from services.converters.pdf import (
    apply_watermark,
    parse_page_range,
    rotate_page_inplace,
    ocr_pdf_to_txt,
    create_searchable_pdf,
    split_pdf_to_pages,
    merge_pdfs,
    extract_text_from_pdf,
    compress_pdf,
    convert_to_pdf,
)

__all__ = [
    "image_file_to_pdf",
    "office_doc_to_pdf",
    "apply_watermark",
    "parse_page_range",
    "rotate_page_inplace",
    "ocr_pdf_to_txt",
    "create_searchable_pdf",
    "split_pdf_to_pages",
    "merge_pdfs",
    "extract_text_from_pdf",
    "compress_pdf",
    "convert_to_pdf",
]
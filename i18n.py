from typing import Dict, Optional

# Хранилище выбранных языков пользователей
USER_LANG: Dict[int, str] = {}

# Язык по умолчанию — английский
DEFAULT_LANG = "en"


def detect_lang(language_code: Optional[str]) -> str:
    """
    Определяет язык по коду Telegram.
    Возвращает 'ru' или 'en'.
    """
    if not language_code:
        return DEFAULT_LANG

    code = language_code.lower()

    # Славянские — считаем русским
    if code.startswith("ru") or code.startswith("uk") or code.startswith("be"):
        return "ru"

    # Всё остальное — английский
    return "en"


def set_user_lang(user_id: int, language_code: Optional[str]) -> str:
    """
    Сохраняет язык в словаре USER_LANG.
    """
    lang = detect_lang(language_code)
    USER_LANG[user_id] = lang
    return lang


def get_user_lang(user_id: int) -> str:
    """
    Возвращает язык пользователя, иначе дефолтный.
    """
    return USER_LANG.get(user_id, DEFAULT_LANG)


# ===== ЛОКАЛИЗАЦИЯ ТЕКСТОВ =====

TEXTS: Dict[str, Dict[str, str]] = {
    "ru": {
        # /start
        "start_main": (
            "👋 Привет! Я конвертирую и обрабатываю файлы в PDF.\n\n"
            "Выбери режим на клавиатуре и пришли файл:\n\n"
            "Основные инструменты:\n"
            "• 📄 Конвертировать в PDF\n"            
            "• 📉 Сжать PDF\n"
            "• 📎 Объединить PDF\n"
            "• ✂️ Разделить PDF\n"
            "• 📝 Извлечь текст\n\n"
            "PRO-инструменты:\n"
            "• 🔍 OCR в текст\n"
            "• 📑 Сделать PDF с выделяемым текстом\n"
            "• 🧩 Редактировать страницы\n"
            "• 🛡 Добавить водяной знак\n\n"
            "Текущий тариф: <b>{tier}</b>\n"
            "Лимит: <b>{limit_mb}</b>\n\n"
            "Подключить PRO-версию: /pro\n\n"
            "Связаться с поддержкой: /support"
        ),
        "footer_legal": (
            "Юридическая информация: используя бота, вы соглашаетесь с "
            '<a href="{terms}">Условиями использования</a> и '
            '<a href="{privacy}">Политикой конфиденциальности</a>.'
        ),        
        # /pro, когда уже есть PRO
        "pro_already": (
            "✅ У вас уже PRO-доступ.\n"
            "Текущий лимит: {max_size}.\n\n"
            "Доступные PRO-инструменты:\n"
            "• OCR (сканы/фото → текст)\n"
            "• Сделать PDF с выделяемым текстом (скан → PDF)\n"
            "• Редактировать страницы PDF (поворот/удаление/извлечение)\n"
            "• Добавить водяные знаки для PDF\n"
            "• Файлы до 100 МБ\n\n"
            "Юридическая информация: используя PRO, вы соглашаетесь с "
            '<a href="{terms}">Условиями использования</a> и '
            '<a href="{privacy}">Политикой конфиденциальности</a>.'
        ),
        # /pro, когда PRO нет
        "pro_info": (
            "💼 <b>PRO-доступ</b>\n\n"
            "Что даёт сейчас:\n"
            "• Лимит до 100 МБ\n"
            "• OCR (сканы и фото → текст)\n"
            "• Searchable PDF (скан → PDF с выделяемым текстом)\n"
            "• Редактор страниц PDF (поворот/удаление/извлечение)\n"
            "• Водяные знаки для PDF\n\n"
            "Оформляя PRO, вы соглашаетесь с "
            '<a href="{terms}">Условиями использования</a> и '
            '<a href="{privacy}">Политикой конфиденциальности</a>.'
        ),
        "privacy_link": "Полную Политику конфиденциальности можно прочитать по ссылке:",
        "terms_link": "Полные Условия использования можно прочитать по ссылке:",    

        # ===== КНОПКИ ОСНОВНОГО МЕНЮ =====
        "btn_main_doc_to_pdf": "📄 Конвертировать в PDF",
        "btn_main_compress": "📉 Сжать PDF",
        "btn_main_merge": "📎 Объединить PDF",
        "btn_main_split": "✂️ Разделить PDF",
        "btn_main_pdf_to_text": "📝 Извлечь текст",
        "btn_main_ocr": "🔍 OCR в текст",
        "btn_main_searchable": "📑 Сделать PDF с выделяемым текстом",
        "btn_main_pages": "🧩 Редактировать страницы",
        "btn_main_watermark": "🛡 Добавить водяной знак",
        # ===== МЕНЮ РЕДАКТОРА СТРАНИЦ =====
        "pages_rotate": "🔄 Поворот страниц",
        "pages_delete": "🗑 Удалить страницы",
        "pages_extract": "📤 Извлечь страницы",
        "pages_cancel": "❌ Отмена",
        "pages_back": "↩️ Назад к меню",

        # ===== ВОДЯНОЙ ЗНАК =====
        "wm_mosaic": "Мозаика",
        "wm_ok": "OK",

        # ===== DOC/IMAGE HANDLER =====
        "err_file_too_big": (
            "Файл слишком большой для тарифа ({tier}).\n"
            "Лимит: {limit}.\n\n"
            "Для больших файлов нужен PRO.\n"
            "Смотрите /pro."
        ),
        "msg_converting_image": "Конвертирую изображение в PDF...",
        "msg_converting_doc": "Конвертирую документ в PDF...",
        "msg_done": "Готово.",
        "err_image_convert": "Не удалось конвертировать изображение.",
        "err_doc_convert": "Ошибка при конвертации документа в PDF.",
        "err_unsupported": (
            "Этот тип файла пока не поддерживается.\n"
            "Поддерживаются: DOC, DOCX, XLS, XLSX, PPT, PPTX и изображения."
        ),

        # ===== MERGE (объединение) =====
        "merge_need_two": "Добавьте минимум 2 PDF.",
        "merge_start": "Объединяю {count} PDF...",
        "merge_error": "Ошибка при объединении.",
        "merge_confirm": "Объединить PDF",

        # ===== РЕЖИМЫ =====
        "mode_compress": "Режим: сжатие PDF. Пришли PDF.",
        "mode_pdf_text": "Режим: PDF → текст. Пришли PDF.",
        "mode_doc_photo": "Режим: DOC/IMG → PDF. Пришли документ или файл-изображение.",
        "mode_merge": (
            "Режим: объединение.\n"
            "Пришли 2–10 PDF-файлов.\n"
            "Потом нажми «Объединить»."
        ),
        "mode_split": "Режим: разделение PDF.\nПришли один PDF.",
        "mode_ocr_free": (
            "Режим: 🔍 OCR (распознавание текста в сканах и фото).\n"
            "Эта функция доступна только для PRO-пользователей.\n\n"
            "Подробнее: /pro"
        ),
        "mode_ocr_pro": (
            "Режим: 🔍 OCR.\n"
            "Пришли PDF-скан или изображение (фото/картинка). "
            "Я верну TXT-файл с распознанным текстом."
        ),
        "mode_searchable_free": (
            "Режим: 📑 Searchable PDF.\n"
            "Делаю из скана PDF с выделяемым текстом.\n"
            "Функция доступна только для PRO-пользователей.\n\n"
            "Подробнее: /pro"
        ),
        "mode_searchable_pro": (
            "Режим: 📑 Searchable PDF.\n"
            "Пришли сканированный PDF. Я верну PDF, "
            "в котором текст можно выделять и искать."
        ),
        "mode_pages_free": (
            "Режим: 🧩 Редактор страниц PDF.\n"
            "Доступно только для PRO-пользователей.\n\n"
            "В этом режиме можно поворачивать, удалять и извлекать страницы.\n"
            "Подробнее: /pro"
        ),
        "mode_pages_pro": (
            "Режим: 🧩 Редактор страниц PDF.\n"
            "Пришли PDF, страницы которого нужно отредактировать."
        ),
        "mode_watermark_free": (
            "Режим: 🛡 водяной знак для PDF.\n"
            "Функция доступна только для PRO-пользователей.\n\n"
            "Подробнее: /pro"
        ),
        "mode_watermark_pro": (
            "Режим: 🛡 Водяной знак.\n"
            "1) Пришли PDF-файл.\n"
            "2) Потом введи текст водяного знака.\n"
            "3) Выбери позицию на сетке и при желании включи Mosaic."
        ),

        # ===== РЕДАКТОР СТРАНИЦ =====
        "pages_pro_only": "Только для PRO.",
        "pages_no_pdf_editor": "Нет загруженного PDF. Сначала пришли файл в режиме редактора.",
        "pages_no_pdf": "Нет загруженного PDF. Сначала пришли файл.",
        "pages_one_page_choose_angle": "В файле 1 страница.\nВыбери угол поворота:",
        "pages_rotate_ask_pages": (
            "Страниц в файле: {num_pages}.\n\n"
            "Какие страницы нужно повернуть?\n\n"
            "Примеры:\n"
            "• 2\n"
            "• 1-3\n"
            "• 1,3,5-7\n"
            "• all"
        ),
        "pages_delete_ask_pages": (
            "Страниц в файле: {num_pages}.\n\n"
            "Какие страницы удалить?\n\n"
            "Примеры:\n"
            "• 2\n"
            "• 1-3\n"
            "• 1,3,5-7"
        ),
        "pages_extract_ask_pages": (
            "Страниц в файле: {num_pages}.\n\n"
            "Какие страницы извлечь?\n\n"
            "Примеры:\n"
            "• 2\n"
            "• 1-3\n"
            "• 1,3,5-7\n"
            "• all"
        ),
        "pages_edit_finished": (
            "Редактирование страниц завершено.\n"
            "Можно выбрать другой режим или прислать PDF для сжатия."
        ),
        "pages_bad_angle": "Некорректный угол.",
        "pages_no_pdf_short": "Нет загруженного PDF.",
        "pages_open_error": "Не удалось открыть PDF.",
        "pages_save_error": "Ошибка при сохранении PDF.",
        "pages_rotated_done": "Готово: страницы повёрнуты на {angle}°.",
        "pages_continue_choose_action": "Можно продолжить редактирование.\nВыбери действие:",
        "pages_no_active_doc": "Нет активного документа. Выбери режим и пришли PDF.",
        "pages_menu_header": (
            "Редактор страниц PDF.\n"
            "Страниц: {num_pages}\n\n"
            "Выбери действие:"
        ),

        # ===== EDITOR ENTRY FROM PDF HANDLER =====
        "pages_pro_only_full": "Редактор страниц доступен только для PRO-пользователей. См. /pro",
        "pages_intro_with_file": (
            "Редактор страниц PDF.\n"
            "Файл: {file_name}\n"
            "Страниц в документе: {num_pages}\n\n"
            "Выбери действие:"
        ),

        # ===== OCR =====
        "ocr_pro_only": "OCR доступен только для PRO-пользователей. См. /pro",
        "msg_ocr_processing": "Распознаю текст в PDF (OCR)...",
        "err_ocr_failed": "Не удалось распознать текст (возможно очень плохое качество скана).",
        "msg_ocr_done": "Готово: OCR-текст из PDF.",

        # ===== SEARCHABLE PDF =====
        "searchable_pro_only": "Searchable PDF доступен только для PRO-пользователей. См. /pro",
        "msg_searchable_processing": "Создаю searchable PDF (можно выделять текст)...",
        "err_searchable_failed": "Ошибка при создании searchable PDF.",
        "msg_searchable_done": "Готово: searchable PDF. Теперь текст можно выделять и искать.",

        # ===== WATERMARK ENTRY =====
        "wm_pro_only": "Водяные знаки доступны только для PRO-пользователей. См. /pro",
        "wm_pdf_received": (
            "PDF получил.\n"
            "Теперь отправь текст водяного знака.\n"
            "Например: CONFIDENTIAL, DRAFT, КОПИЯ."
        ),

        # ===== MERGE FROM PDF HANDLER =====
        "merge_too_many": "Можно объединить не больше 10 файлов за раз.",
        "merge_file_added": (
            "Добавил файл #{count} для объединения.\n"
            "Пришли ещё PDF или нажми «Объединить»."
        ),

        # ===== PDF → TEXT =====
        "msg_extracting_text": "Извлекаю текст...",
        "err_no_text_found": "Текста не найдено (возможно скан или ошибка чтения).",

        # ===== SPLIT =====
        "msg_splitting_pdf": "Разделяю PDF...",
        "err_open_pdf": "Не удалось открыть PDF.",
        "err_only_one_page": "Там всего 1 страница.",
        "split_page_caption": "Страница {i}/{n}",
        "split_zip_done": "Готово: {n} страниц в ZIP.",

        # ===== COMPRESS =====
        "msg_compressing_pdf": "Сжимаю PDF...",
        "err_compress_failed": "Не удалось сжать PDF (ошибка Ghostscript).",

        # ===== РЕДАКТОР СТРАНИЦ — TEXT HANDLER =====
        "pages_rotate_range_failed": (
            "Не удалось распознать страницы.\n"
            "Примеры: 2, 1-3, 1,3,5-7 или all."
        ),
        "pages_rotate_confirm": (
            "Страницы для поворота: {raw}.\n"
            "Теперь выбери угол поворота:"
        ),
        "pages_angle_reminder": "Выбери угол поворота с помощью кнопок под предыдущим сообщением.",
        "pages_delete_range_failed": (
            "Не удалось распознать страницы для удаления.\n"
            "Примеры: 2, 1-3, 1,3,5-7."
        ),
        "pages_delete_all_removed": "После удаления не осталось ни одной страницы. Операция отменена.",
        "pages_delete_done": "Готово: удалены страницы {raw}. Осталось страниц: {kept}.",
        "pages_continue_editing_full": (
            "Можно продолжить редактирование страниц:\n"
            "— Поворот\n"
            "— Удаление\n"
            "— Извлечение\n\n"
            "Выбери действие:"
        ),
        "pages_extract_range_failed": (
            "Не удалось распознать страницы для извлечения.\n"
            "Примеры: 2, 1-3, 1,3,5-7 или all."
        ),
        "pages_extract_done": "Готово: извлечены страницы {raw} в отдельный PDF.",
        "pages_continue_source_edit": (
            "Можно продолжить редактирование исходного файла.\n"
            "Выбери действие:"
        ),

        # ===== ВОДЯНОЙ ЗНАК — TEXT HANDLER =====
        "wm_no_pdf": "Не нашёл PDF для водяного знака. Начни заново и пришли PDF.",
        "wm_empty_text": "Текст пустой. Отправь текст водяного знака ещё раз.",
        "wm_choose_pos_full": (
            "Выбери позицию водяного знака (сетку 3×3) и при необходимости включи Mosaic."
        ),
        "wm_style_reminder": "Используй кнопки под прошлым сообщением для выбора позиции и Mosaic.",

        # ===== ВОДЯНОЙ ЗНАК — CALLBACK HANDLER =====
        "wm_no_data": "Нет данных для водяного знака, начни заново.",
        "wm_applying": "Добавляю водяной знак в PDF...",
        "wm_save_failed": "Не получилось сохранить PDF с водяным знаком.",
        "wm_done": "Готово: PDF с водяным знаком.",
        
        # ===== ОПЛАТА PRO =====
        "pro_info": (
            "💼 <b>PRO-доступ</b>\n\n"
            "Что даёт:\n"
            "• Лимит до 100 МБ\n"
            "• OCR (сканы и фото → текст)\n"
            "• Searchable PDF (скан → PDF с выделяемым текстом)\n"
            "• Редактор страниц PDF (поворот/удаление/извлечение)\n"
            "• Водяные знаки\n\n"
            "Выберите срок подписки с помощью кнопок ниже.\n\n"
            "Оформляя PRO, вы соглашаетесь с "
            '<a href="{terms}">Условиями использования</a> и '
            '<a href="{privacy}">Политикой конфиденциальности</a>.'
        ),

        "pro_activated": (
            "✅ Подписка PRO активирована!\n"
            "Лимит увеличен до 100 МБ, PRO-инструменты доступны."
        ),

        "pro_pay_button": "Оплатить PRO",
        "pro_pay_hint": (
            "💼 <b>PRO-доступ</b>\n\n"
            "Оплатите PRO через Telegram Stars."
        ),

        # Этот блок сейчас нигде не используется, но пусть будет без долларов
        "pro_info_short": (
            "💼 <b>PRO-доступ</b>\n\n"
            "Открывает все инструменты:\n"
            "• До <b>100 МБ</b> на файл\n"
            "• <b>OCR</b> для сканов и фото\n"
            "• <b>Searchable PDF</b>\n"
            "• <b>Редактор страниц</b>\n"
            "• <b>Водяные знаки</b>\n\n"
            "Выберите срок подписки с помощью кнопок ниже 👇"
        ),

        "pro_btn_month": "🔹 PRO на 1 месяц",
        "pro_btn_quarter": "🔸 PRO на 3 месяца",
        "pro_btn_year": "🏆 PRO на 12 месяцев",
        "pro_manage_btn": "🔧 Управлять подпиской",

        # ===== ПОДДЕРЖКА =====
        "support_intro": (
            "🆘 <b>Связаться с поддержкой</b>\n\n"
            "Напиши одним следующим сообщением, в чём проблема или вопрос.\n"
            "Я перешлю его разработчику бота.\n\n"
            "Чтобы отменить, отправь /support_cancel."
        ),
        "support_sent": (
            "✅ Сообщение отправлено разработчику.\n"
            "Обычно он отвечает в личные сообщения в Telegram."
        ),
        "support_error": (
            "❌ Не удалось отправить сообщение в поддержку.\n"
            "Попробуй позже или напиши напрямую, если знаешь контакт."
        ),
        "support_cancelled": "Режим поддержки отменён.",
        "support_not_waiting": "Сейчас бот не ждёт от тебя сообщение для поддержки.",
        
        "support_usage": (
            "🆘 <b>Связаться с поддержкой</b>\n\n"
            "Отправь команду в формате:\n"
            "<code>/support твой вопрос или описание проблемы</code>\n\n"
            "Пример:\n"
            "<code>/support Не конвертируется файл, бот пишет ошибку</code>"
        ),
                
        
    },

    "en": {
        "start_main": (
            "👋 Hi! I convert and process files to PDF.\n\n"
            "Choose a mode on the keyboard and send a file:\n\n"
            "Main tools:\n"
            "• 📄 Convert to PDF\n"
            "• 📉 Compress PDF\n"
            "• 📎 Merge PDFs\n"
            "• ✂️ Split PDF\n"
            "• 📝 Extract text\n\n"
            "PRO tools:\n"
            "• 🔍 OCR to text\n"
            "• 📑 Make searchable\n"
            "• 🧩 Edit pages\n"
            "• 🛡 Add watermark\n\n"
            "Current plan: <b>{tier}</b>\n"
            "Limit: <b>{limit_mb}</b>\n\n"
            "Upgrade to PRO: /pro\n\n"
            "Contact support: /support"
            
        ),
        "footer_legal": (
            "Legal: by using this bot you agree to the "
            '<a href="{terms}">Terms of Use</a> and '
            '<a href="{privacy}">Privacy Policy</a>.'
        ),        
        "pro_already": (
            "✅ You already have PRO access.\n"
            "Current limit: {max_size}.\n\n"
            "Available PRO features:\n"
            "• OCR (scans/photos → text)\n"
            "• Searchable PDF (scan → PDF with selectable text)\n"
            "• PDF page editor (rotate/delete/extract)\n"
            "• PDF watermarks\n"
            "• Files up to 100 MB"
        ),
        "pro_info_short": (
            "💼 <b>PRO access</b>\n\n"
            "• Limit up to 100 MB\n"
            "• OCR (scans and photos → text)\n"
            "• Searchable PDF\n"
            "• PDF page editor\n"
            "• Watermarks\n\n"
            "Tap the button below to get PRO via Stripe."
        ),
        "pro_info": (
            "💼 <b>PRO access</b>\n\n"
            "What you get now:\n"
            "• Limit up to 100 MB\n"
            "• OCR for scans and photos\n"
            "• Searchable PDF\n"
            "• PDF page editor (rotate/delete/extract)\n"
            "• Watermarks\n\n"
            "To get PRO, tap the payment button.\n\n"
            "By subscribing, you agree to the "
            '<a href="{terms}">Terms of Use</a> and '
            '<a href="{privacy}">Privacy Policy</a>.'
        ),        
        "pro_pay_button": "💳 Get PRO",

        # ===== MAIN MENU BUTTONS =====
        "btn_main_doc_to_pdf": "📄 Convert to PDF",
        "btn_main_compress": "📉 Compress PDF",
        "btn_main_merge": "📎 Merge PDFs",
        "btn_main_split": "✂️ Split PDF",
        "btn_main_pdf_to_text": "📝 Extract text",
        "btn_main_ocr": "🔍 OCR to text",
        "btn_main_searchable": "📑 Make searchable",
        "btn_main_pages": "🧩 Edit pages",
        "btn_main_watermark": "🛡 Add watermark",

        # ===== PAGES EDITOR MENU =====
        "pages_rotate": "🔄 Rotate pages",
        "pages_delete": "🗑 Delete pages",
        "pages_extract": "📤 Extract pages",
        "pages_cancel": "❌ Cancel",
        "pages_back": "↩️ Back to menu",

        # ===== WATERMARK =====
        "wm_mosaic": "Mosaic",
        "wm_ok": "OK",

        # ===== DOC/IMAGE HANDLER =====
        "err_file_too_big": (
            "The file is too large for your plan ({tier}).\n"
            "Limit: {limit}.\n\n"
            "Large files require PRO.\n"
            "See /pro."
        ),
        "msg_converting_image": "Converting image to PDF...",
        "msg_converting_doc": "Converting document to PDF...",
        "msg_done": "Done.",
        "err_image_convert": "Failed to convert image.",
        "err_doc_convert": "Error converting document to PDF.",
        "err_unsupported": (
            "This file type is not supported.\n"
            "Supported: DOC, DOCX, XLS, XLSX, PPT, PPTX, and images."
        ),

        # ===== MERGE (combine PDFs) =====
        "merge_need_two": "Add at least 2 PDF files.",
        "merge_start": "Merging {count} PDFs...",
        "merge_error": "Error while merging PDFs.",
        "merge_confirm": "Merge PDFs",

        # ===== MODES =====
        "mode_compress": "Mode: compress PDF. Send a PDF file.",
        "mode_pdf_text": "Mode: PDF → text. Send a PDF file.",
        "mode_doc_photo": "Mode: DOC/IMG → PDF. Send a document or image file.",
        "mode_merge": (
            "Mode: merge PDFs.\n"
            "Send 2–10 PDF files.\n"
            "Then tap “Merge”."
        ),
        "mode_split": "Mode: split PDF.\nSend one PDF file.",
        "mode_ocr_free": (
            "Mode: 🔍 OCR (text recognition in scans/photos).\n"
            "This feature is available only for PRO users.\n\n"
            "More: /pro"
        ),
        "mode_ocr_pro": (
            "Mode: 🔍 OCR.\n"
            "Send a scanned PDF or image (photo/picture). "
            "I will return a TXT file with recognized text."
        ),
        "mode_searchable_free": (
            "Mode: 📑 Searchable PDF.\n"
            "I make a PDF with selectable text from a scan.\n"
            "This feature is available only for PRO users.\n\n"
            "More: /pro"
        ),
        "mode_searchable_pro": (
            "Mode: 📑 Searchable PDF.\n"
            "Send a scanned PDF. I will return a PDF "
            "where text can be selected and searched."
        ),
        "mode_pages_free": (
            "Mode: 🧩 PDF page editor.\n"
            "Available only for PRO users.\n\n"
            "In this mode you can rotate, delete and extract pages.\n"
            "More: /pro"
        ),
        "mode_pages_pro": (
            "Mode: 🧩 PDF page editor.\n"
            "Send the PDF whose pages you want to edit."
        ),
        "mode_watermark_free": (
            "Mode: 🛡 PDF watermark.\n"
            "This feature is available only for PRO users.\n\n"
            "More: /pro"
        ),
        "mode_watermark_pro": (
            "Mode: 🛡 Watermark.\n"
            "1) Send a PDF file.\n"
            "2) Then enter the watermark text.\n"
            "3) Choose a position on the grid and optionally enable Mosaic."
        ),

        # ===== PAGES EDITOR =====
        "pages_pro_only": "PRO only.",
        "pages_no_pdf_editor": "No PDF is loaded. First send a file in editor mode.",
        "pages_no_pdf": "No PDF is loaded. First send a file.",
        "pages_one_page_choose_angle": "The file has 1 page.\nChoose a rotation angle:",
        "pages_rotate_ask_pages": (
            "Pages in file: {num_pages}.\n\n"
            "Which pages should be rotated?\n\n"
            "Examples:\n"
            "• 2\n"
            "• 1-3\n"
            "• 1,3,5-7\n"
            "• all"
        ),
        "pages_delete_ask_pages": (
            "Pages in file: {num_pages}.\n\n"
            "Which pages should be deleted?\n\n"
            "Examples:\n"
            "• 2\n"
            "• 1-3\n"
            "• 1,3,5-7"
        ),
        "pages_extract_ask_pages": (
            "Pages in file: {num_pages}.\n\n"
            "Which pages should be extracted?\n\n"
            "Examples:\n"
            "• 2\n"
            "• 1-3\n"
            "• 1,3,5-7\n"
            "• all"
        ),
        "pages_edit_finished": (
            "Page editing finished.\n"
            "You can choose another mode or send a PDF to compress."
        ),
        "pages_bad_angle": "Invalid angle.",
        "pages_no_pdf_short": "No PDF is loaded.",
        "pages_open_error": "Failed to open PDF.",
        "pages_save_error": "Error saving PDF.",
        "pages_rotated_done": "Done: pages rotated by {angle}°.",
        "pages_continue_choose_action": "You can continue editing.\nChoose an action:",
        "pages_no_active_doc": "No active document. Choose a mode and send a PDF.",
        "pages_menu_header": (
            "PDF page editor.\n"
            "Pages: {num_pages}\n\n"
            "Choose an action:"
        ),

        # ===== EDITOR ENTRY FROM PDF HANDLER =====
        "pages_pro_only_full": "Page editor is available only for PRO users. See /pro",
        "pages_intro_with_file": (
            "PDF page editor.\n"
            "File: {file_name}\n"
            "Pages in document: {num_pages}\n\n"
            "Choose an action:"
        ),

        # ===== OCR =====
        "ocr_pro_only": "OCR is available only for PRO users. See /pro",
        "msg_ocr_processing": "Running OCR on PDF...",
        "err_ocr_failed": "Failed to recognize text (scan quality might be too low).",
        "msg_ocr_done": "Done: OCR text from PDF.",

        # ===== SEARCHABLE PDF =====
        "searchable_pro_only": "Searchable PDF is available only for PRO users. See /pro",
        "msg_searchable_processing": "Creating searchable PDF (selectable text)...",
        "err_searchable_failed": "Error while creating searchable PDF.",
        "msg_searchable_done": "Done: searchable PDF. Now text can be selected and searched.",

        # ===== WATERMARK ENTRY =====
        "wm_pro_only": "Watermarks are available only for PRO users. See /pro",
        "wm_pdf_received": (
            "PDF received.\n"
            "Now send the watermark text.\n"
            "For example: CONFIDENTIAL, DRAFT, COPY."
        ),

        # ===== MERGE FROM PDF HANDLER =====
        "merge_too_many": "You can merge up to 10 files at a time.",
        "merge_file_added": (
            "File #{count} added for merging.\n"
            "Send more PDFs or tap “Merge”."
        ),

        # ===== PDF → TEXT =====
        "msg_extracting_text": "Extracting text...",
        "err_no_text_found": "No text found (maybe a scan or read error).",

        # ===== SPLIT =====
        "msg_splitting_pdf": "Splitting PDF...",
        "err_open_pdf": "Failed to open PDF.",
        "err_only_one_page": "There is only 1 page.",
        "split_page_caption": "Page {i}/{n}",
        "split_zip_done": "Done: {n} pages in ZIP.",

        # ===== COMPRESS =====
        "msg_compressing_pdf": "Compressing PDF...",
        "err_compress_failed": "Failed to compress PDF (Ghostscript error).",

        # ===== PAGES EDITOR — TEXT HANDLER =====
        "pages_rotate_range_failed": (
            "Could not parse pages.\n"
            "Examples: 2, 1-3, 1,3,5-7 or all."
        ),
        "pages_rotate_confirm": (
            "Pages to rotate: {raw}.\n"
            "Now choose a rotation angle:"
        ),
        "pages_angle_reminder": "Choose a rotation angle using the buttons under the previous message.",
        "pages_delete_range_failed": (
            "Could not parse pages to delete.\n"
            "Examples: 2, 1-3, 1,3,5-7."
        ),
        "pages_delete_all_removed": "After deleting, no pages are left. Operation cancelled.",
        "pages_delete_done": "Done: pages {raw} deleted. Pages left: {kept}.",
        "pages_continue_editing_full": (
            "You can continue editing pages:\n"
            "— Rotate\n"
            "— Delete\n"
            "— Extract\n\n"
            "Choose an action:"
        ),
        "pages_extract_range_failed": (
            "Could not parse pages to extract.\n"
            "Examples: 2, 1-3, 1,3,5-7 or all."
        ),
        "pages_extract_done": "Done: pages {raw} extracted to a separate PDF.",
        "pages_continue_source_edit": (
            "You can continue editing the original file.\n"
            "Choose an action:"
        ),

        # ===== WATERMARK — TEXT HANDLER =====
        "wm_no_pdf": "Could not find a PDF for watermark. Start again and send a PDF.",
        "wm_empty_text": "Text is empty. Send the watermark text again.",
        "wm_choose_pos_full": (
            "Choose the watermark position (3×3 grid) and enable Mosaic if needed."
        ),
        "wm_style_reminder": "Use the buttons under the previous message to choose position and Mosaic.",

        # ===== WATERMARK — CALLBACK HANDLER =====
        "wm_no_data": "No data for watermark, please start again.",
        "wm_applying": "Applying watermark to PDF...",
        "wm_save_failed": "Failed to save PDF with watermark.",
        "wm_done": "Done: PDF with watermark.",

        # ===== PRO PAYMENT =====
        "pro_info": (
            "💼 <b>PRO access</b>\n\n"
            "You get:\n"
            "• Limit up to 100 MB\n"
            "• OCR for scans and photos\n"
            "• Searchable PDF\n"
            "• PDF page editor (rotate/delete/extract)\n"
            "• Watermarks\n\n"
            "Choose the subscription period using the buttons below.\n\n"
            "By subscribing, you agree to the "
            '<a href="{terms}">Terms of Use</a> and '
            '<a href="{privacy}">Privacy Policy</a>.'
        ),

        "pro_activated": (
            "✅ PRO subscription has been activated!\n"
            "Limit increased to 100 MB, PRO tools are now available."
        ),

        "pro_pay_button": "Get PRO",
        "pro_pay_hint": (
            "💼 <b>PRO access</b>\n\n"
            "Pay for PRO via Telegram Stars."
        ),

        "pro_info_short": (
            "💼 <b>PRO access</b>\n\n"
            "Unlocks all premium tools:\n"
            "• Up to <b>100 MB</b> per file\n"
            "• <b>OCR</b> for scans/photos\n"
            "• <b>Searchable PDF</b>\n"
            "• <b>Page editor</b>\n"
            "• <b>Watermarks</b>\n\n"
            "Choose the subscription period using the buttons below 👇"
        ),

        "pro_btn_month": "🔹 PRO for 1 month",
        "pro_btn_quarter": "🔸 PRO for 3 months",
        "pro_btn_year": "🏆 PRO for 12 months",
        "pro_manage_btn": "🔧 Manage subscription",

        # ===== SUPPORT =====
        "support_intro": (
            "🆘 <b>Contact support</b>\n\n"
            "Send your question or issue as the next message.\n"
            "I will forward it to the bot developer.\n\n"
            "To cancel, send /support_cancel."
        ),
        "support_sent": (
            "✅ Your message has been sent to the developer.\n"
            "They will usually reply to you in Telegram DM."
        ),
        "support_error": (
            "❌ Failed to send the message to support.\n"
            "Please try again later or contact the developer directly if you have their contact."
        ),
        "support_cancelled": "Support mode cancelled.",
        "support_not_waiting": "The bot is not waiting for a support message from you right now.",
        
        "support_usage": (
            "🆘 <b>Contact support</b>\n\n"
            "Use the command in the format:\n"
            "<code>/support your question or issue</code>\n\n"
            "Example:\n"
            "<code>/support The bot fails to convert my file</code>"
        ),

    },
}


def _get_text_for_lang(lang: str, key: str) -> str:
    lang_dict = TEXTS.get(lang)
    if not lang_dict:
        lang_dict = TEXTS[DEFAULT_LANG]

    if key in lang_dict:
        return lang_dict[key]

    # если нет ключа — fallback на английский
    default_dict = TEXTS[DEFAULT_LANG]
    return default_dict.get(key, f"[{key}]")  # крайний случай


def t(user_id: int, key: str, **kwargs) -> str:
    lang = get_user_lang(user_id)
    text = _get_text_for_lang(lang, key)

    if kwargs:
        return text.format(**kwargs)

    return text

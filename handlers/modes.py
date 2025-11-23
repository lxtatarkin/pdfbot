
    @router.message(F.text == "📉 Сжать PDF")
    async def mode_compress(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "compress"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer("Режим: сжатие PDF. Пришли PDF.", reply_markup=get_main_keyboard())

    @router.message(F.text == "📝 PDF → текст")
    async def mode_pdf_text(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "pdf_text"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer("Режим: PDF → текст. Пришли PDF.", reply_markup=get_main_keyboard())

    @router.message(F.text == "📄 Документ/фото → PDF")
    async def mode_doc_photo(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "doc_photo"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer(
            "Режим: DOC/IMG → PDF. Пришли документ или файл-изображение.",
            reply_markup=get_main_keyboard()
        )

    @router.message(F.text == "📎 Объединить PDF")
    async def mode_merge(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "merge"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer(
            "Режим: объединение.\n"
            "Пришли 2–10 PDF-файлов.\n"
            "Потом напиши «Готово».",
            reply_markup=get_main_keyboard()
        )

    @router.message(F.text == "✂️ Разделить PDF")
    async def mode_split(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "split"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        await message.answer(
            "Режим: разделение PDF.\nПришли один PDF.",
            reply_markup=get_main_keyboard()
        )

    @router.message(F.text == "🔍 OCR")
    async def mode_ocr(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "ocr"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        if not is_pro(user_id):
            await message.answer(
                "Режим: 🔍 OCR (распознавание текста в сканах и фото).\n"
                "Эта функция доступна только для PRO-пользователей.\n\n"
                "Подробнее: /pro"
            )
        else:
            await message.answer(
                "Режим: 🔍 OCR.\n"
                "Пришли PDF-скан или изображение (фото/картинка). Я верну TXT-файл с распознанным текстом."
            )

    @router.message(F.text == "📑 Searchable PDF")
    async def mode_searchable_pdf(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "searchable_pdf"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}
        if not is_pro(user_id):
            await message.answer(
                "Режим: 📑 Searchable PDF.\n"
                "Делаю из скана PDF с выделяемым текстом.\n"
                "Функция доступна только для PRO-пользователей.\n\n"
                "Подробнее: /pro"
            )
        else:
            await message.answer(
                "Режим: 📑 Searchable PDF.\n"
                "Пришли сканированный PDF. Я верну PDF, в котором текст можно выделять и искать."
            )

    @router.message(F.text == "🧩 Редактор страниц")
    async def mode_pages(message: types.Message):
        user_id = message.from_user.id
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}

        if not is_pro(user_id):
            user_modes[user_id] = "compress"
            await message.answer(
                "Режим: 🧩 Редактор страниц PDF.\n"
                "Доступно только для PRO-пользователей.\n\n"
                "В этом режиме можно поворачивать, удалять и извлекать страницы.\n"
                "Подробнее: /pro"
            )
        else:
            user_modes[user_id] = "pages_wait_pdf"
            await message.answer(
                "Режим: 🧩 Редактор страниц PDF.\n"
                "Пришли PDF, страницы которого нужно отредактировать.",
                reply_markup=get_main_keyboard()
            )

    @router.message(F.text == "🛡 Водяной знак")
    async def mode_watermark(message: types.Message):
        user_id = message.from_user.id
        user_modes[user_id] = "watermark"
        user_merge_files[user_id] = []
        user_watermark_state[user_id] = {}
        user_pages_state[user_id] = {}

        if not is_pro(user_id):
            await message.answer(
                "Режим: 🛡 водяной знак для PDF.\n"
                "Функция доступна только для PRO-пользователей.\n\n"
                "Подробнее: /pro"
            )
        else:
            await message.answer(
                "Режим: 🛡 Водяной знак.\n"
                "1) Пришли PDF-файл.\n"
                "2) Потом введи текст водяного знака.\n"
                "3) Выбери позицию на сетке и при желании включи Mosaic."
            )
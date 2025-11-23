    # ================================
    #   CALLBACKS: PAGES EDITOR
    # ================================
    @router.callback_query(F.data == "pages_action:rotate")
    async def pages_rotate_action(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not is_pro(user_id):
            await callback.answer("Только для PRO.", show_alert=True)
            return

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await callback.answer("Нет загруженного PDF. Сначала пришли файл в режиме редактора.", show_alert=True)
            return

        if num_pages == 1:
            # одна страница — сразу просим угол
            state["rotate_pages"] = [1]
            user_pages_state[user_id] = state
            user_modes[user_id] = "pages_rotate_wait_angle"

            await callback.message.answer(
                "В файле 1 страница.\n"
                "Выбери угол поворота:",
                reply_markup=get_rotate_keyboard()
            )
        else:
            # несколько страниц — сначала спрашиваем какие
            user_modes[user_id] = "pages_rotate_wait_pages"
            await callback.message.answer(
                f"Страниц в файле: {num_pages}.\n\n"
                "Какие страницы нужно повернуть?\n\n"
                "Примеры:\n"
                "• 2            — только 2 страницу\n"
                "• 1-3          — страницы 1,2,3\n"
                "• 1,3,5-7      — страницы 1,3,5,6,7\n"
                "• all          — все страницы"
            )

        await callback.answer()

    @router.callback_query(F.data == "pages_action:delete")
    async def pages_delete_action(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not is_pro(user_id):
            await callback.answer("Только для PRO.", show_alert=True)
            return

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await callback.answer("Нет загруженного PDF. Сначала пришли файл в режиме редактора.", show_alert=True)
            return

        user_modes[user_id] = "pages_delete_wait_pages"
        await callback.message.answer(
            f"Страниц в файле: {num_pages}.\n\n"
            "Какие страницы удалить?\n\n"
            "Примеры:\n"
            "• 2            — только 2 страницу\n"
            "• 1-3          — страницы 1,2,3\n"
            "• 1,3,5-7      — страницы 1,3,5,6,7"
        )
        await callback.answer()

    @router.callback_query(F.data == "pages_action:extract")
    async def pages_extract_action(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not is_pro(user_id):
            await callback.answer("Только для PRO.", show_alert=True)
            return

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await callback.answer("Нет загруженного PDF. Сначала пришли файл в режиме редактора.", show_alert=True)
            return

        user_modes[user_id] = "pages_extract_wait_pages"
        await callback.message.answer(
            f"Страниц в файле: {num_pages}.\n\n"
            "Какие страницы извлечь в новый PDF?\n\n"
            "Примеры:\n"
            "• 2            — только 2 страницу\n"
            "• 1-3          — страницы 1,2,3\n"
            "• 1,3,5-7      — страницы 1,3,5,6,7\n"
            "• all          — весь документ (копия)"
        )
        await callback.answer()

    @router.callback_query(F.data == "pages_action:cancel")
    async def pages_cancel_action(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        user_pages_state[user_id] = {}
        user_modes[user_id] = "compress"

        await callback.message.answer(
            "Редактирование страниц завершено.\n"
            "Можно выбрать другой режим или прислать PDF для сжатия."
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("pages_rotate_angle:"))
    async def pages_rotate_angle_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        data = callback.data.split(":", 1)[1]  # "+90" / "-90" / "180"
        try:
            angle = int(data)
        except ValueError:
            await callback.answer("Некорректный угол.", show_alert=True)
            return

        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not is_pro(user_id):
            await callback.answer("Только для PRO.", show_alert=True)
            return

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            await callback.answer("Нет загруженного PDF.", show_alert=True)
            user_modes[user_id] = "compress"
            return

        rotate_pages = state.get("rotate_pages")
        if not rotate_pages:
            # если по какой-то причине страниц нет — считаем, что все
            rotate_pages = list(range(1, num_pages + 1))

        try:
            reader = PdfReader(str(pdf_path))
        except Exception as e:
            logger.error(f"Pages rotate open error: {e}")
            await callback.message.answer("Не удалось открыть PDF.")
            await callback.answer()
            return

        writer = PdfWriter()
        rotate_set = set(rotate_pages)
        for idx, page in enumerate(reader.pages, start=1):
            if idx in rotate_set:
                rotate_page_inplace(page, angle)
            writer.add_page(page)

        out_path = FILES_DIR / f"{Path(pdf_path).stem}_rotated.pdf"
        try:
            with open(out_path, "wb") as f:
                writer.write(f)
        except Exception as e:
            logger.error(f"Pages rotate write error: {e}")
            await callback.message.answer("Ошибка при сохранении PDF после поворота.")
            await callback.answer()
            return

        await callback.message.answer_document(
            types.FSInputFile(out_path),
            caption=f"Готово: страницы повёрнуты на {angle}°."
        )

        # обновляем стейт, очищаем rotate_pages
        state["pdf_path"] = out_path
        state["pages"] = num_pages
        state.pop("rotate_pages", None)
        user_pages_state[user_id] = state
        user_modes[user_id] = "pages_menu"

        await callback.message.answer(
            "Можно продолжить редактирование страниц.\n"
            "Выбери действие:",
            reply_markup=get_pages_menu_keyboard()
        )
        await callback.answer()

    @router.callback_query(F.data == "pages_back_to_menu")
    async def pages_back_to_menu_callback(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        state = user_pages_state.get(user_id) or {}
        pdf_path = state.get("pdf_path")
        num_pages = state.get("pages")

        if not pdf_path or not Path(pdf_path).exists() or not num_pages:
            user_modes[user_id] = "compress"
            await callback.message.answer("Нет активного документа. Выбери режим и пришли PDF.")
        else:
            user_modes[user_id] = "pages_menu"
            await callback.message.answer(
                f"Редактор страниц PDF.\n"
                f"Страниц в документе: {num_pages}\n\n"
                "Выбери действие:",
                reply_markup=get_pages_menu_keyboard()
            )

        await callback.answer()
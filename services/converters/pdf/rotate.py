def rotate_page_inplace(page, angle: int) -> None:
    """
    Поворачивает страницу PyPDF2 на указанный угол (кратный 90).
    Работает и с PyPDF2 >= 3.0.0 (page.rotate), и со старыми версиями.
    """
    from settings import logger as _logger

    angle = angle % 360
    if angle == 0:
        return

    rotate_method = getattr(page, "rotate", None)
    if callable(rotate_method):
        rotate_method(angle)
        return

    try:
        if angle == 90:
            page.rotateClockwise(90)
        elif angle == 180:
            page.rotateClockwise(180)
        elif angle == 270:
            page.rotateCounterClockwise(90)
    except Exception as e:
        _logger.error(f"Page rotate fallback error: {e}")
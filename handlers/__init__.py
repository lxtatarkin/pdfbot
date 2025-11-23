from .start import router as start_router
from .modes import router as modes_router
from .pdf import router as pdf_router
from .doc_image import router as doc_image_router
from .photo import router as photo_router
from .text_handlers import router as text_router
from .pages import router as pages_router
from .watermark import router as watermark_router
from .merge import router as merge_router

routers = [
    start_router,
    modes_router,
    pdf_router,
    doc_image_router,
    photo_router,
    text_router,
    pages_router,
    watermark_router,
    merge_router,
]

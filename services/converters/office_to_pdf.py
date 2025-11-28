import subprocess
import zipfile
from pathlib import Path

from settings import FILES_DIR, logger


def has_embedded_fonts(docx_path: Path) -> bool:
    """
    Проверяет, есть ли в DOCX встроенные шрифты (Embed fonts).

    Логика:
    - DOCX = zip-архив
    - шрифты лежат в word/fonts/*.odttf
    - в word/fontTable.xml есть теги <w:embedRegular>, <w:embedBold> и т.п.
    """
    docx_path = Path(docx_path)

    if docx_path.suffix.lower() != ".docx":
        return False

    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            names = z.namelist()

            # 1) наличие встроенных шрифтов как файлов
            for name in names:
                lower = name.lower()
                if lower.startswith("word/fonts/") and lower.endswith(".odttf"):
                    return True

            # 2) анализ fontTable.xml
            if "word/fontTable.xml" in names:
                xml = z.read("word/fontTable.xml")
                markers = [
                    b"<w:embedRegular",
                    b"<w:embedBold",
                    b"<w:embedItalic",
                    b"<w:embedBoldItalic",
                ]
                if any(m in xml for m in markers):
                    return True

        return False

    except zipfile.BadZipFile:
        logger.warning("BadZipFile while checking embedded fonts: %s", docx_path)
        return False
    except Exception as e:
        logger.exception("Error while checking embedded fonts in %s: %s", docx_path, e)
        return False


def office_doc_to_pdf(src_path: Path) -> Path | None:
    """
    Конвертирует офисный документ (DOC/DOCX/XLSX/PPTX...) в PDF через LibreOffice.
    Работает в Docker/Railway через xvfb-run.

    Дополнительно:
    - если это DOCX, перед конвертацией логируем, есть ли встроенные шрифты (Embed fonts).
    """
    src_path = Path(src_path)

    # Логика Embed fonts для DOCX (вариант 3 + вариант 2 под капотом)
    if src_path.suffix.lower() == ".docx":
        embedded = has_embedded_fonts(src_path)
        logger.info(
            "DOCX embedded fonts check: %s (file=%s)",
            embedded,
            src_path,
        )

    lo_path = "soffice"  # в контейнере Linux
    logger.info("LibreOffice binary: %s", lo_path)

    FILES_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        "xvfb-run",
        "--auto-servernum",
        "--server-args=-screen 0 1024x768x24",
        lo_path,
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        "--convert-to",
        "pdf:writer_pdf_Export",
        "--outdir",
        str(FILES_DIR),
        str(src_path),
    ]
    logger.info("Running LibreOffice: %s", " ".join(cmd))

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    logger.info("LibreOffice return code: %s", proc.returncode)
    logger.info("LibreOffice stdout: %s", (proc.stdout or "").strip())
    logger.info("LibreOffice stderr: %s", (proc.stderr or "").strip())

    if proc.returncode != 0:
        logger.error("LibreOffice failed with nonzero exit code")
        return None

    pdf_candidates = list(FILES_DIR.glob("*.pdf"))
    logger.info("PDF candidates found: %s", pdf_candidates)

    if not pdf_candidates:
        logger.error("PDF not found after LibreOffice conversion.")
        return None

    pdf_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return pdf_candidates[0]
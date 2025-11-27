import subprocess
from pathlib import Path

from settings import FILES_DIR, logger


def office_doc_to_pdf(src_path: Path) -> Path | None:
    """
    Конвертирует офисный документ (DOC/DOCX/XLSX/PPTX...) в PDF через LibreOffice.
    Работает в Docker/Railway через xvfb-run.
    """
    lo_path = "soffice"  # в контейнере Linux
    logger.info(f"LibreOffice binary: {lo_path}")

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
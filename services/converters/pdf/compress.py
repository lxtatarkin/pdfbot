import subprocess
from pathlib import Path

from settings import logger


def compress_pdf(input_path: Path, output_path: Path) -> bool:
    """
    Сжимает PDF через Ghostscript.
    Возвращает True при успехе, False при ошибке.
    """
    gs_cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/ebook",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        str(input_path),
    ]

    try:
        result = subprocess.run(
            gs_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as e:
        logger.error(f"Ghostscript run error: {e}")
        return False

    if result.returncode != 0:
        logger.error(f"Ghostscript exit code {result.returncode}: {result.stderr}")
        return False

    return output_path.exists()
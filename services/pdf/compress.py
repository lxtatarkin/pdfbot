from pathlib import Path
import subprocess
from settings import logger


def compress_pdf(input_path: Path, output_path: Path) -> bool:
    """
    Сжатие PDF через Ghostscript.
    Возвращает True при успехе, False при ошибке.
    """

    try:
        cmd = [
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

        subprocess.run(cmd, check=True)
        return True

    except Exception as e:
        logger.error(f"PDF compress error: {e}")
        return False
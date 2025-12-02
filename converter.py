# converter.py
import zipfile
from pathlib import Path
import subprocess


def has_embedded_fonts(docx_path: str) -> bool:
    docx_path = Path(docx_path)

    if docx_path.suffix.lower() != ".docx":
        return False

    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            names = z.namelist()

            # Основной индикатор — встроенные шрифты (.odttf)
            for name in names:
                lower = name.lower()
                if lower.startswith("word/fonts/") and lower.endswith(".odttf"):
                    return True

            # Дополнительная проверка fontTable.xml
            if "word/fontTable.xml" in names:
                xml = z.read("word/fontTable.xml")
                keywords = [
                    b"<w:embedRegular",
                    b"<w:embedBold",
                    b"<w:embedItalic",
                    b"<w:embedBoldItalic",
                ]
                if any(k in xml for k in keywords):
                    return True

        return False

    except zipfile.BadZipFile:
        return False


def convert_with_libreoffice(input_file: str, output_dir: str) -> str:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "soffice",
            "--headless",
            "--nologo",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            input_file,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return str(output_dir / (Path(input_file).stem + ".pdf"))


def convert_docx_smart(input_docx: str, output_dir: str):
    embedded = has_embedded_fonts(input_docx)
    pdf_path = convert_with_libreoffice(input_docx, output_dir)
    return pdf_path, embedded

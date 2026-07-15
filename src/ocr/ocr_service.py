import pypdfium2 as pdfium
import pytesseract

from src.core.config import get_platform, load_config
from src.core.logger import logger

# Render-Auflösung für PDF→Bild vor der OCR. 200 dpi entspricht dem
# bisherigen pdf2image-Default; PDF-Koordinaten sind 72 dpi → Skalierung.
_RENDER_DPI = 200
_RENDER_SCALE = _RENDER_DPI / 72


def _configure_ocr():
    """Liest die OCR-Einstellungen und setzt den Tesseract-Pfad.

    Bewusst pro Aufruf statt auf Modulebene: ein Config-Problem soll beim
    OCR-Lauf einen behandelbaren Fehler geben, nicht schon beim Import des
    Moduls die ganze App verhindern.
    """
    config = load_config()
    platform_name = get_platform()

    tesseract_path = config["ocr"]["tesseract"][platform_name]

    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    return config["ocr"].get("language") or "deu+eng"


def extract_text_from_image_pdf(pdf_path):
    logger.info(f"OCR gestartet: {pdf_path}")

    language = _configure_ocr()

    pdf = pdfium.PdfDocument(pdf_path)
    text = ""

    try:
        for page in pdf:
            image = page.render(scale=_RENDER_SCALE).to_pil()
            page_text = pytesseract.image_to_string(image, lang=language)
            text += page_text + "\n"

    finally:
        pdf.close()

    logger.info(f"OCR abgeschlossen: {pdf_path}")

    return text


def extract_text_from_image(image_path):
    language = _configure_ocr()

    text = pytesseract.image_to_string(image_path, lang=language)

    logger.info(f"OCR abgeschlossen: {image_path}")

    return text

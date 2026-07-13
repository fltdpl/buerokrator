import pytesseract
from pdf2image import convert_from_path

from src.core.config import get_platform, load_config
from src.core.logger import logger


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

    language = config["ocr"].get("language") or "deu+eng"
    poppler_path = config["ocr"]["poppler"][platform_name]

    return language, poppler_path


def extract_text_from_image_pdf(pdf_path):
    logger.info(f"OCR gestartet: {pdf_path}")

    language, poppler_path = _configure_ocr()

    if poppler_path:
        images = convert_from_path(pdf_path, poppler_path=poppler_path)

    else:
        images = convert_from_path(pdf_path)

    text = ""

    for image in images:
        page_text = pytesseract.image_to_string(image, lang=language)
        text += page_text + "\n"

    logger.info(f"OCR abgeschlossen: {pdf_path}")

    return text


def extract_text_from_image(image_path):
    language, _ = _configure_ocr()

    text = pytesseract.image_to_string(image_path, lang=language)

    logger.info(f"OCR abgeschlossen: {image_path}")

    return text

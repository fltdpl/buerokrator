import pytesseract
from pdf2image import convert_from_path
from src.core.logger import logger


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

POPPLER_PATH = (
    r"C:\Program Files\poppler\poppler-26.02.0\Library\bin"
)

def extract_text_from_image_pdf(pdf_path):
    logger.info(
        f"OCR gestartet: {pdf_path}"
    )
    images = convert_from_path(
        pdf_path,
        poppler_path=POPPLER_PATH
    )
    text = ""

    for image in images:
        page_text = pytesseract.image_to_string(
            image,
            lang="deu+eng"
        )
        text += page_text + "\n"

    logger.info(
        f"OCR abgeschlossen: {pdf_path}"
    )

    return text


def extract_text_from_image(image_path):

    text = pytesseract.image_to_string(
        image_path,
        lang="deu+eng"
    )

    logger.info(
        f"OCR abgeschlossen: {image_path}"
    )

    return text
import pytesseract
from src.core.logger import logger

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

def extract_text_from_image(image_path):
    logger.info(
        f"OCR gestartet: {image_path}"
    )
    text = pytesseract.image_to_string(
        image_path,
        lang="deu+eng"
    )
    logger.info(
        f"OCR abgeschlossen: {image_path}"
    )
    return text
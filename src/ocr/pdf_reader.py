from pypdf import PdfReader
from src.core.logger import logger


def has_text(pdf_path):
    reader = PdfReader(pdf_path)

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text and page_text.strip():
            return True

    return False


def extract_text(pdf_path):
    logger.info(f"PDF wird gelesen: {pdf_path}")
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    logger.info(
        f"Textextraktion abgeschlossen: {pdf_path}"
    )

    return text



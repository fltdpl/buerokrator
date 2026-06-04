import time
from pathlib import Path
from src.core.logger import logger
from src.ocr.pdf_reader import (
    extract_text as pdf_extract_text,
    has_text
)
from src.ocr.ocr_service import (
    extract_text_from_image_pdf,
    extract_text_from_image
)
from src.classifier.document_classifier import classify



def get_file_type(file_path):
    return Path(file_path).suffix.lower()

def validate_document(file_path):
    logger.info(f"Validierung gestartet: {file_path}")
    print("Validierung")

def wait_for_file(file_path):
    for _ in range(10):
        try:
            with open(file_path, "rb"):
                return True
        except PermissionError:
            time.sleep(0.5)
    return False


def extract_text(file_path):
    logger.info(f"Textextraktion gestartet: {file_path}")
    file_type = get_file_type(file_path)
    if file_type == ".pdf":
        if has_text(file_path):
            logger.info("PDF enthält bereits Text")
            text = pdf_extract_text(file_path)

        else:
            logger.info("PDF enthält keinen Text - OCR erforderlich")
            print("OCR erforderlich")

            text = extract_text_from_image_pdf(file_path)
    
    elif file_type in [".png", ".jpg", ".jpeg"]:
        logger.info("PNG, JPG, JPEG enthält keinen Text - OCR erforderlich")
        print("OCR erforderlich")
        text = extract_text_from_image(file_path)

    else:
        raise ValueError(f"Dateityp nicht unterstützt: {file_type}")

    logger.info(f"{len(text)} Zeichen extrahiert")
    print(f"{len(text)} Zeichen extrahiert")
    return text


def classify_document(file_path, document_text):

    logger.info(f"Klassifikation gestartet: {file_path}")
    classification = classify(document_text)
    print(f"Dokumenttyp: {classification['document_type']}")
    logger.info(f"Dokumenttyp erkannt: {classification['document_type']}")

    return classification


def archive_document(file_path, classification):
    logger.info(
        f"Archivierung gestartet: {file_path}"
    )
    print(
        f"Archivierung ({classification['document_type']})"
    )


def process(file_path):
    logger.info(
        f"Verarbeitung gestartet: {file_path}"
    )
    print(
        f"Verarbeite Dokument: {file_path}"
    )
    try:
        if not wait_for_file(file_path):
            raise Exception(
                f"Datei konnte nicht geöffnet werden: {file_path}"
            )
        
        validate_document(file_path)
        
        document_text = extract_text(file_path)

        logger.info(
            f"Textlänge: {len(document_text)}"
        )
        print(
            f"Textlänge: {len(document_text)}"
        )
        classification = classify_document(
            file_path,
            document_text
        )
        archive_document(file_path, classification)
        logger.info(
            f"Verarbeitung abgeschlossen: {file_path}"
        )

    except Exception as e:
        logger.error(
            f"{type(e).__name__}: Fehler bei der Verarbeitung des Dokuments {file_path}: {e}"
        )
        print(
            f"Fehler bei der Verarbeitung: {e}"
        )
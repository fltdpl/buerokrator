import shutil
import time
from datetime import datetime
from pathlib import Path

from src.classifier.document_classifier import classify

# from src.classifier.rule_classifier import classify
from src.classifier.document_extractor import extract_invoice
from src.core.logger import logger
from src.ocr.ocr_service import extract_text_from_image, extract_text_from_image_pdf
from src.ocr.pdf_reader import extract_text as pdf_extract_text
from src.ocr.pdf_reader import has_text
from src.organizer.filename_builder import build_filename

year = str(datetime.now().year)


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
        logger.info("Bilddatei erkannt - OCR erforderlich")
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


def extract_document_data(classification, document_text):
    document_type = classification["document_type"]
    if document_type == "invoice":
        print("Rechnungsdaten extrahieren...")
        extracted_data = extract_invoice(document_text)

        return extracted_data

    return {}


def archive_document(file_path, classification, extracted_data):

    document_type = classification["document_type"]

    target_folder = Path("archive") / year / document_type

    target_folder.mkdir(parents=True, exist_ok=True)

    new_filename = build_filename(classification, extracted_data, file_path)

    source = Path(file_path)

    target = target_folder / new_filename

    target = get_unique_target_path(target)

    shutil.move(str(source), str(target))

    logger.info(f"Datei archiviert: {target}")

    print(f"Datei archiviert: {target}")


def get_unique_target_path(target):

    original_stem = target.stem
    suffix = target.suffix
    counter = 1

    while target.exists():
        target = target.parent / f"{original_stem}_{counter}{suffix}"

        counter += 1

    return target


def process(file_path):
    logger.info(f"Verarbeitung gestartet: {file_path}")
    print(f"Verarbeite Dokument: {file_path}")
    try:
        if not wait_for_file(file_path):
            raise Exception(f"Datei konnte nicht geöffnet werden: {file_path}")

        validate_document(file_path)

        document_text = extract_text(file_path)

        logger.info(f"Textlänge: {len(document_text)}")

        print(f"Textlänge: {len(document_text)}")

        classification = classify_document(file_path, document_text)

        extracted_data = extract_document_data(classification, document_text)

        print(f"Extrahierte Daten: {extracted_data}")

        if extracted_data is None:
            extracted_data = {}
        archive_document(file_path, classification, extracted_data)

        logger.info(f"Verarbeitung abgeschlossen: {file_path}")

    except Exception as e:
        logger.error(
            f"{type(e).__name__}: Fehler bei der Verarbeitung des Dokuments {file_path}: {e}"
        )
        print(f"Fehler bei der Verarbeitung: {e}")

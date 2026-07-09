import shutil
import time
from pathlib import Path

from src.classifier.document_classifier import classify
from src.classifier.document_extractor import extract_document
from src.core.file_hash import file_hash
from src.core.logger import logger
from src.database.document_repository import insert_document
from src.database.find_duplicate import find_document_by_hash
from src.organizer.trash import move_to_trash
from src.ocr.ocr_service import extract_text_from_image, extract_text_from_image_pdf
from src.ocr.pdf_reader import extract_text as pdf_extract_text
from src.ocr.pdf_reader import has_text
from src.organizer.category_mapper import get_archive_category
from src.organizer.date_utils import extract_year
from src.organizer.filename_builder import (
    build_filename,
    get_unique_target_path,
)


def get_file_type(file_path):
    return Path(file_path).suffix.lower()


def validate_document(file_path):
    logger.info(f"Validierung gestartet: {file_path}")


def wait_for_file(file_path):
    """Wartet, bis die Datei lesbar ist und ihre Größe stabil bleibt.

    Ein reiner Öffnen-Test genügt nicht: Unter Linux ist eine noch nicht
    fertig kopierte Datei bereits öffenbar. Deshalb wird zusätzlich auf eine
    über zwei Messungen konstante, nicht-leere Dateigröße gewartet.
    """
    path = Path(file_path)
    last_size = -1

    for _ in range(20):
        try:
            with open(path, "rb"):
                pass
            current_size = path.stat().st_size

        except (PermissionError, FileNotFoundError):
            time.sleep(0.5)
            continue

        if current_size > 0 and current_size == last_size:
            return True

        last_size = current_size
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
    print(f"{document_type} Daten extrahieren...")

    return extract_document(document_type, document_text)


def archive_document(file_path, classification, extracted_data):

    document_type = classification["document_type"]
    category = get_archive_category(document_type)
    year = extract_year(extracted_data)
    target_folder = Path("archive") / year / category
    target_folder.mkdir(parents=True, exist_ok=True)
    new_filename = build_filename(classification, extracted_data, file_path)
    source = Path(file_path)
    target = target_folder / new_filename
    target = get_unique_target_path(target)
    shutil.move(str(source), str(target))

    logger.info(f"Datei archiviert: {target}")
    print(f"Datei archiviert: {target}")

    return target


def analyze_document(file_path):
    if not wait_for_file(file_path):
        raise Exception(f"Datei konnte nicht geöffnet werden: {file_path}")

    validate_document(file_path)

    document_text = extract_text(file_path)
    logger.info(f"Textlänge: {len(document_text)}")

    classification = classify_document(file_path, document_text)
    extracted_data = extract_document_data(classification, document_text)

    if extracted_data is None:
        extracted_data = {}

    return {
        "classification": classification,
        "extracted_data": extracted_data,
        "document_text": document_text,
    }


def archive_analyzed_document(
    file_path,
    classification,
    extracted_data,
    document_text=None,
    content_hash=None,
):

    archive_path = archive_document(
        file_path,
        classification,
        extracted_data,
    )

    document_id = insert_document(
        filename=archive_path.name,
        archive_path=str(archive_path),
        document_type=classification["document_type"],
        extracted_data=extracted_data,
        document_text=document_text,
        content_hash=content_hash,
    )

    return archive_path, document_id


def process(file_path):
    """Verarbeitet eine Datei komplett.

    Gibt bei Erfolg ein Ergebnis-dict zurück (truthy, für das Frontend:
    was wurde erkannt, wohin archiviert), bei Fehler None (falsy).
    Ist die Datei eine Dublette eines bereits archivierten Dokuments, trägt
    das Ergebnis `duplicate_of` und die Datei wandert unverarbeitet in den
    Papierkorb.
    """
    logger.info(f"Verarbeitung gestartet: {file_path}")
    print(f"Verarbeite Dokument: {file_path}")
    try:
        if not wait_for_file(file_path):
            raise Exception(f"Datei konnte nicht geöffnet werden: {file_path}")

        # Vor OCR und LLM: eine Dublette soll den Rechner nicht beschäftigen.
        content_hash = file_hash(file_path)
        duplicate = find_document_by_hash(content_hash)

        if duplicate:
            duplicate_id, duplicate_name = duplicate
            trashed = move_to_trash(file_path)
            logger.info(
                f"Dublette von #{duplicate_id} ({duplicate_name}),"
                f" in den Papierkorb verschoben: {trashed}"
            )

            return {
                "source_name": Path(file_path).name,
                "duplicate_of": duplicate_id,
                "duplicate_filename": duplicate_name,
            }

        result = analyze_document(file_path)

        archive_path, document_id = archive_analyzed_document(
            file_path,
            result["classification"],
            result["extracted_data"],
            document_text=result["document_text"],
            content_hash=content_hash,
        )

        logger.info(f"Verarbeitung abgeschlossen: {file_path}")

        return {
            "source_name": Path(file_path).name,
            "document_id": document_id,
            "document_type": result["classification"]["document_type"],
            "filename": archive_path.name,
            "archive_path": str(archive_path),
        }

    except Exception as e:
        logger.error(
            f"{type(e).__name__}: Fehler bei der Verarbeitung des Dokuments {file_path}: {e}"
        )
        print(f"Fehler bei der Verarbeitung: {e}")

        return None

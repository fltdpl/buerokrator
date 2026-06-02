from src.core.logger import logger


def validate_document(file_path):
    logger.info(f"Validierung gestartet: {file_path}")
    print("Validierung")


def extract_text(file_path):
    logger.info(f"Textextraktion gestartet: {file_path}")
    print("Textextraktion")


def classify_document(file_path):
    logger.info(f"Klassifikation gestartet: {file_path}")
    print("Klassifikation")


def archive_document(file_path):
    logger.info(f"Archivierung gestartet: {file_path}")
    print("Archivierung")


def process(file_path):
    logger.info(f"Verarbeitung gestartet: {file_path}")
    print(f"Verarbeite Dokument: {file_path}")

    try:
        validate_document(file_path)
        extract_text(file_path)
        classify_document(file_path)
        archive_document(file_path)
        logger.info(f"Verarbeitung abgeschlossen: {file_path}")
    except Exception as e:
        logger.error(f"{type(e).__name__}: Fehler bei der Verarbeitung des Dokuments {file_path}: {e}")
        print(f"Fehler bei der Verarbeitung: {e}")
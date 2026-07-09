from pathlib import Path

from src.core.config import load_config
from src.processor.document_processor import process

DEFAULT_SUPPORTED_TYPES = [".pdf", ".png", ".jpg", ".jpeg"]


def _supported_types(config):
    types = config.get("supported_file_types") or DEFAULT_SUPPORTED_TYPES
    return {suffix.lower() for suffix in types}


def find_inbox_documents():
    """Listet alle unterstützten Dateien im Inbox-Ordner (sortiert)."""
    config = load_config()
    inbox = Path(config["paths"]["inbox"])

    if not inbox.exists():
        return []

    supported = _supported_types(config)

    return sorted(
        path
        for path in inbox.iterdir()
        if path.is_file() and path.suffix.lower() in supported
    )


def import_inbox_documents(progress_callback=None):
    """Verarbeitet alle Dokumente im Inbox-Ordner.

    progress_callback(index, total, filename) wird vor jeder Datei aufgerufen.
    Gibt (erfolgreich, dubletten, fehlgeschlagen) zurück: erfolgreich und
    dubletten als Listen von Ergebnis-dicts aus process(), fehlgeschlagen als
    Liste von Dateinamen. Dubletten sind kein Fehler — sie sind bereits
    archiviert und werden nur gemeldet.
    """
    files = find_inbox_documents()

    succeeded = []
    duplicates = []
    failed = []

    total = len(files)

    for index, path in enumerate(files):
        if progress_callback:
            progress_callback(index, total, path.name)

        result = process(str(path))

        if not result:
            failed.append(path.name)

        elif "duplicate_of" in result:
            duplicates.append(result)

        else:
            succeeded.append(result)

    return succeeded, duplicates, failed

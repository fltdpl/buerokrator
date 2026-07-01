import shutil
from pathlib import Path

from src.core.config import load_config
from src.core.logger import logger
from src.database.database import get_connection
from src.database.init_database import init_database


def clear_archive():
    """Löscht alle Dokumente im Archivordner (Unterordner und Dateien).

    Der Archivordner selbst bleibt bestehen. Gibt die Anzahl der entfernten
    Einträge (oberste Ebene) zurück.
    """
    config = load_config()
    archive_path = Path(config["paths"]["archive"])

    removed = 0

    if archive_path.exists():
        for child in archive_path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)

            else:
                child.unlink()

            removed += 1

    return removed


def reset_documents_table():
    """Verwirft die documents-Tabelle und legt das Schema neu an."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS documents")

    conn.commit()
    conn.close()

    init_database()


def reset_database_and_archive():
    """Löscht alle archivierten Dokumente und initialisiert die Datenbank neu.

    Gibt die Anzahl der entfernten Archiv-Einträge zurück.
    """
    removed = clear_archive()
    reset_documents_table()

    logger.warning(
        f"Datenbank und Archiv zurückgesetzt ({removed} Archiv-Einträge entfernt)"
    )

    return removed

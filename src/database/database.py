import sqlite3
from pathlib import Path

from src.core.config import load_config

_schema_ready = False


def _ensure_schema():
    """Führt die Schema-Migration einmal pro Prozess aus.

    So läuft die Migration automatisch beim ersten Datenbankzugriff (App-Start),
    statt nur in Tests oder beim manuellen Zurücksetzen.
    """
    global _schema_ready
    if _schema_ready:
        return

    # Flag zuerst setzen, um Rekursion zu vermeiden (init_database nutzt selbst
    # get_connection).
    _schema_ready = True

    from src.database.init_database import init_database

    init_database()


def get_connection():
    config = load_config()

    db_path = config["database"]["path"]
    Path(db_path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _ensure_schema()

    return sqlite3.connect(db_path)

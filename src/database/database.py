import sqlite3
from contextlib import contextmanager
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

    # timeout: wartet bei gesperrter DB, statt sofort "database is locked"
    # zu werfen (der Stapel-Import schreibt in einem Thread, die UI liest
    # parallel).
    conn = sqlite3.connect(db_path, timeout=10)
    # Zeilen als sqlite3.Row: Zugriff per Spaltenname statt per Position.
    # Schützt davor, dass ein neues Feld die Indizes aller Konsumenten
    # verschiebt (die expliziten SELECTs und SELECT * hatten verified/created_at
    # sogar in unterschiedlicher Reihenfolge).
    conn.row_factory = sqlite3.Row
    # WAL: Leser blockieren Schreiber nicht (und umgekehrt). Der Modus ist
    # in der DB-Datei persistent; das PRAGMA pro Verbindung ist billig.
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def open_connection():
    """get_connection mit garantiertem close — auch im Fehlerfall.

    Für alle DB-Zugriffe der Persistenzschicht: `with open_connection() as
    conn:` statt manuellem conn.close(), damit eine Exception zwischen
    Öffnen und Schließen keine Verbindung (und damit ggf. eine Schreibsperre)
    offen hält.
    """
    conn = get_connection()

    try:
        yield conn

    finally:
        conn.close()

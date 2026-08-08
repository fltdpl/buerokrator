import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from src.core.config import load_config

_schema_ready = False

# Serialisiert die Migration: der Stapel-Import läuft in einem eigenen
# Thread, während die UI weiter liest.
_schema_lock = threading.Lock()

# Thread, der gerade migriert. init_database ruft selbst get_connection —
# dieser eine Thread muss durchgelassen werden, sonst blockiert er sich
# an der eigenen Sperre.
_migrating_thread: "int | None" = None


def _ensure_schema() -> None:
    """Führt die Schema-Migration einmal pro Prozess aus.

    So läuft die Migration automatisch beim ersten Datenbankzugriff (App-Start),
    statt nur in Tests oder beim manuellen Zurücksetzen.

    Das Fertig-Flag wird NACH der Migration gesetzt und die Migration von
    einer Sperre geschützt: vorher zog ein zweiter Thread am noch laufenden
    init_database vorbei und arbeitete auf einem Schema ohne Tabellen.
    Scheitert die Migration, bleibt das Flag false — der nächste Zugriff
    versucht es erneut, statt den Fehler für die Prozesslaufzeit
    festzuschreiben.
    """
    global _schema_ready, _migrating_thread

    if _schema_ready:
        return

    if _migrating_thread == threading.get_ident():
        return

    with _schema_lock:
        # Zweite Prüfung: ein anderer Thread kann inzwischen fertig sein.
        if _schema_ready:
            return

        from src.database.init_database import init_database

        _migrating_thread = threading.get_ident()

        try:
            init_database()

            # Die DB enthält OCR-Volltexte aller Dokumente — nur für den
            # Besitzer lesbar. Einmal pro Prozess; die WAL-/SHM-Dateien
            # erben die Rechte der Hauptdatei.
            db_path = load_config()["database"]["path"]

            try:
                os.chmod(db_path, 0o600)

            except OSError:
                pass

            _schema_ready = True

        finally:
            _migrating_thread = None


def reset_schema_state() -> None:
    """Vergisst, dass das Schema fertig ist — nach einem Profilwechsel nötig.

    Das Flag gilt pro Prozess, nicht pro Datenbank. Ohne diesen Reset würde
    die Datenbank des neu gewählten Profils nie angelegt oder migriert: der
    erste Zugriff sähe ein gesetztes Flag und liefe an `init_database`
    vorbei — auf ein Schema ohne Tabellen.
    """
    global _schema_ready

    with _schema_lock:
        _schema_ready = False


def get_connection() -> sqlite3.Connection:
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
def open_connection() -> "Iterator[sqlite3.Connection]":
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

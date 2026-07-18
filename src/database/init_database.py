import os
import sqlite3
from datetime import datetime
from pathlib import Path

from src.core.config import load_config
from src.core.logger import logger
from src.database.database import open_connection

# Schemastand der DB (PRAGMA user_version). Bei jeder Schemaänderung um 1
# erhöhen — Bestands-DBs (auch Version 0 = vor Einführung der Versionierung)
# bekommen dann vor der Migration automatisch ein Backup neben der DB-Datei.
SCHEMA_VERSION = 3


DOCUMENT_COLUMNS = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "filename": "TEXT",
    "archive_path": "TEXT",
    "document_type": "TEXT",
    "extracted_data": "TEXT",
    "created_at": "TEXT",
    "verified": "INTEGER DEFAULT 0",
    "document_text": "TEXT",
    "notes": "TEXT",
    "tax_year": "TEXT",
    # SHA-256 des Originals; Dubletten-Erkennung beim Import. Altbestand hat
    # NULL — dort greift die Erkennung erst nach einem Neu-Import.
    "content_hash": "TEXT",
    # Steuerrelevanz (0/1). NULL = noch nicht gesetzt: dann gilt der aus
    # Typ/Subtyp abgeleitete Default (siehe src/tax/tax_relevance.py).
    "tax_relevant": "INTEGER",
    # Steuerlicher Zweck eines Beleg-Dokuments (werbungskosten /
    # krankheitskosten, NULL = keiner). Vom Nutzer beim Prüfen gesetzt,
    # nie vom LLM; Grundlage der Belegsummen-Positionen im ELSTER-Mapping.
    "tax_purpose": "TEXT",
}

REQUIRED_EXISTING_COLUMNS = {
    "id",
}


def get_existing_columns(cursor):
    rows = cursor.execute(
        """
        PRAGMA table_info(documents)
        """
    ).fetchall()

    return {row["name"] for row in rows}


def migrate_documents_table(cursor):
    existing_columns = get_existing_columns(cursor)
    missing_required_columns = REQUIRED_EXISTING_COLUMNS - existing_columns

    if missing_required_columns:
        missing = ", ".join(sorted(missing_required_columns))
        raise RuntimeError(
            f"Inkompatibles documents-Schema. Fehlende Spalten: {missing}"
        )

    for column_name, column_definition in DOCUMENT_COLUMNS.items():
        if column_name in existing_columns:
            continue

        cursor.execute(
            f"""
            ALTER TABLE documents
            ADD COLUMN {column_name} {column_definition}
            """
        )


def create_indexes(cursor):
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documents_document_type
        ON documents (document_type)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documents_created_at
        ON documents (created_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documents_content_hash
        ON documents (content_hash)
        """
    )


# Spalten, die die Volltextsuche indexiert (Reihenfolge = FTS-Spaltenindex,
# relevant für die bm25-Gewichte in search.py).
FTS_COLUMNS = ["filename", "document_type", "extracted_data", "document_text", "notes"]


def create_fts(cursor):
    """Legt die FTS5-Volltexttabelle samt Sync-Triggern an (Schema v2).

    External-Content-Tabelle über documents: der Index speichert die Texte
    nicht doppelt; Trigger halten ihn bei INSERT/UPDATE/DELETE aktuell.
    Trigram-Tokenizer: Substring-Suche wie das frühere LIKE, aber indiziert
    und mit Relevanz-Ranking (bm25).
    """
    fts_exists = (
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'documents_fts'
            """
        ).fetchone()
        is not None
    )

    columns = ", ".join(FTS_COLUMNS)

    cursor.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
            {columns},
            content='documents',
            content_rowid='id',
            tokenize='trigram'
        )
        """
    )

    new_columns = ", ".join(f"new.{name}" for name in FTS_COLUMNS)
    old_columns = ", ".join(f"old.{name}" for name in FTS_COLUMNS)

    # DROP + CREATE statt IF NOT EXISTS: falls sich die Spaltenliste einmal
    # ändert, bleiben sonst veraltete Trigger stehen.
    for name in ("documents_fts_ai", "documents_fts_ad", "documents_fts_au"):
        cursor.execute(f"DROP TRIGGER IF EXISTS {name}")

    cursor.execute(
        f"""
        CREATE TRIGGER documents_fts_ai AFTER INSERT ON documents BEGIN
            INSERT INTO documents_fts (rowid, {columns})
            VALUES (new.id, {new_columns});
        END
        """
    )
    cursor.execute(
        f"""
        CREATE TRIGGER documents_fts_ad AFTER DELETE ON documents BEGIN
            INSERT INTO documents_fts (documents_fts, rowid, {columns})
            VALUES ('delete', old.id, {old_columns});
        END
        """
    )
    cursor.execute(
        f"""
        CREATE TRIGGER documents_fts_au AFTER UPDATE ON documents BEGIN
            INSERT INTO documents_fts (documents_fts, rowid, {columns})
            VALUES ('delete', old.id, {old_columns});
            INSERT INTO documents_fts (rowid, {columns})
            VALUES (new.id, {new_columns});
        END
        """
    )

    # Frisch angelegte FTS-Tabelle: Bestand einmalig indexieren (Migration
    # v1→v2, aber auch nach Backup-Restore einer älteren DB).
    if not fts_exists:
        cursor.execute(
            "INSERT INTO documents_fts (documents_fts) VALUES ('rebuild')"
        )


def _backup_before_migration(conn, old_version):
    """Sichert die DB-Datei, bevor eine Migration sie verändert.

    Bewusst neben die DB statt ans konfigurierte Backup-Ziel (das kann ein
    nicht eingehängtes externes Laufwerk sein). Nutzt die SQLite-Backup-API,
    damit auch nicht eingespielte WAL-Inhalte mitkommen.
    """
    db_path = Path(load_config()["database"]["path"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(
        f"pre_migration_v{old_version}_zu_v{SCHEMA_VERSION}_{timestamp}.db"
    )

    backup_conn = sqlite3.connect(backup_path)

    try:
        conn.backup(backup_conn)

    finally:
        backup_conn.close()

    # Wie die Haupt-DB: OCR-Volltexte, nur für den Besitzer lesbar.
    try:
        os.chmod(backup_path, 0o600)

    except OSError:
        pass

    logger.info("Backup vor Schema-Migration angelegt: %s", backup_path)


def init_database():
    with open_connection() as conn:
        cursor = conn.cursor()

        version = cursor.execute("PRAGMA user_version").fetchone()["user_version"]

        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Die Datenbank hat Schemaversion {version}, diese "
                f"Programmversion kennt nur {SCHEMA_VERSION}. Vermutlich "
                "wurde die Datenbank mit einer neueren Buerokrator-Version "
                "benutzt — bitte Programm aktualisieren."
            )

        documents_exists = (
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'documents'
                """
            ).fetchone()
            is not None
        )

        # Nur echte Bestands-DBs mit älterem Schemastand sichern — eine
        # frische DB (noch keine Tabelle) hat nichts zu verlieren.
        if documents_exists and version < SCHEMA_VERSION:
            _backup_before_migration(conn, version)

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS documents (
                {", ".join(
                    f"{name} {definition}"
                    for name, definition in DOCUMENT_COLUMNS.items()
                )}
            )
            """,
        )

        migrate_documents_table(cursor)
        create_indexes(cursor)
        create_fts(cursor)

        cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

        conn.commit()


if __name__ == "__main__":
    init_database()

    print("Datenbank initialisiert.")

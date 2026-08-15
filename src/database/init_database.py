import os
import sqlite3
from datetime import datetime
from pathlib import Path

from src.core.app_home import get_app_home
from src.core.config import load_config
from src.core.logger import logger
from src.database.database import open_connection

# Schemastand der DB (PRAGMA user_version). Bei jeder Schemaänderung um 1
# erhöhen — Bestands-DBs (auch Version 0 = vor Einführung der Versionierung)
# bekommen dann vor der Migration automatisch ein Backup neben der DB-Datei.
SCHEMA_VERSION = 7


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
    # Abgeleitet aus den Tag-Zuordnungen, damit die Volltextsuche sie
    # findet: der FTS-Index hängt an `documents`, die Zuordnungen liegen in
    # eigenen Tabellen und wären für ihn sonst unsichtbar. Geschrieben wird
    # die Spalte ausschließlich von src/database/tags.py.
    "tags_text": "TEXT",
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
FTS_COLUMNS = [
    "filename",
    "document_type",
    "extracted_data",
    "document_text",
    "notes",
    # Immer HINTEN anhängen: die Reihenfolge bestimmt den Spaltenindex der
    # Fundstelle (search._SNIPPET_COLUMN) und die Zuordnung der
    # bm25-Gewichte. Eine Einfügung in der Mitte verschöbe beides still.
    "tags_text",
]


def _fts_columns_match(cursor):
    """Stimmt die Spaltenliste der vorhandenen FTS-Tabelle noch?

    Wächst FTS_COLUMNS, muss der Index neu gebaut werden — eine
    Virtual Table lässt sich nicht per ALTER erweitern, und ein stehen
    gelassener alter Index fände die neue Spalte nie.
    """
    vorhanden = [row["name"] for row in cursor.execute("PRAGMA table_info(documents_fts)")]

    return vorhanden == FTS_COLUMNS


def backfill_tags_text(cursor):
    """Trägt `tags_text` für Bestandszeilen nach.

    Ohne das fände die Suche Tags, die vor der Erweiterung vergeben wurden,
    nie — und niemand käme darauf, warum ausgerechnet die alten fehlen.
    Dokumente ohne Tags bekommen '' statt NULL, damit der Nachtrag nicht bei
    jedem Start erneut über den ganzen Bestand läuft.
    """
    cursor.execute(
        """
        UPDATE documents
        SET tags_text = COALESCE(
            (
                SELECT group_concat(tags.name, ' ')
                FROM document_tags
                JOIN tags ON tags.id = document_tags.tag_id
                WHERE document_tags.document_id = documents.id
            ),
            ''
        )
        WHERE tags_text IS NULL
        """
    )


def relativize_archive_paths(cursor):
    """Speichert `archive_path` relativ zum App-Home (Schema v7).

    Bis v6 stand der Pfad absolut in der Datenbank. Damit war jeder
    Ortswechsel des Bestands ein stiller Totalausfall: die Werte sahen
    richtig aus, nur die Datei war "nicht gefunden" (der Fehlerfall von
    0.3.1). Relativ gespeichert wandert der Bezugspunkt mit.

    Läuft bei JEDEM Start, nicht nur beim Versionssprung — die Anweisung ist
    idempotent (danach beginnt kein Wert mehr mit dem Präfix) und heilt
    damit auch Zeilen, die eine ältere Fassung der Reparatur wieder absolut
    geschrieben hat. Pfade außerhalb des App-Home bleiben unberührt: sie
    sind ein bewusst gewählter Ort und keine Speicherform.

    Bewusst als reines SQL statt einer Schleife über den Bestand — eine
    Tabellenprüfung je Start, kein Zeilenverkehr nach Python.
    """
    prefix = f"{get_app_home()}{os.sep}"

    cursor.execute(
        """
        UPDATE documents
        SET archive_path = substr(archive_path, ?)
        WHERE substr(archive_path, 1, ?) = ?
        """,
        (len(prefix) + 1, len(prefix), prefix),
    )


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

    # Gewachsene Spaltenliste: neu bauen. Der Neuaufbau ist billig, weil die
    # Tabelle External Content ist — sie liest alles aus `documents` zurück.
    if fts_exists and not _fts_columns_match(cursor):
        cursor.execute("DROP TABLE documents_fts")
        fts_exists = False

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


def _drop_verworfene_tag_tabellen(cursor):
    """Entfernt die Tag-Tabellen des verworfenen ersten Entwurfs.

    Der erste Entwurf hatte eine Spalte `namespace` (Tags als
    „namensraum:wert"). Er wurde vor der Veröffentlichung verworfen, liegt
    aber auf Entwicklungsmaschinen schon in Datenbanken —
    `CREATE TABLE IF NOT EXISTS` ließe sie stumm stehen, und jede Abfrage
    liefe danach gegen fehlende Spalten.

    Nur wenn nichts drinsteht: Tags gab es nie in einer Veröffentlichung,
    ein gefüllter Bestand kann also nur ein Missverständnis sein — und
    stillschweigend Daten zu löschen wäre der schlimmere Fehler.
    """
    vorhanden = cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name = 'tags'
        """
    ).fetchone()

    if vorhanden is None:
        return

    spalten = {row["name"] for row in cursor.execute("PRAGMA table_info(tags)")}

    if "namespace" not in spalten:
        return

    belegt = cursor.execute("SELECT COUNT(*) AS n FROM tags").fetchone()["n"]

    if belegt:
        raise RuntimeError(
            "Die Tabelle 'tags' stammt aus einem verworfenen Entwurf, "
            "enthält aber Einträge. Bitte melden — automatisch wird hier "
            "nichts gelöscht."
        )

    cursor.execute("DROP TABLE IF EXISTS document_tags")
    cursor.execute("DROP TABLE tags")
    logger.info("Tag-Tabellen des verworfenen Entwurfs entfernt (waren leer).")


def create_tag_tables(cursor):
    """Tags und ihre Zuordnung (Schema v5).

    Zwei Tabellen statt einer Spalte auf `documents`: ein Dokument trägt
    beliebig viele Tags, und dieselbe Vokabel soll an vielen Dokumenten
    hängen, ohne dass ihre Schreibweise mehrfach gespeichert wird.

    Tags sind **flach** — ein Wert, keine Systematik. Zwei Spalten für den
    Namen: `name` ist die Schreibweise für die Anzeige (deutsche Substantive
    kleinzuschreiben sähe falsch aus), `key` der casefold-Vergleichswert und
    die eigentliche Eindeutigkeit. `COLLATE NOCASE` wäre die naheliegende
    Alternative gewesen und scheidet aus: es faltet nur ASCII, „Ärzte" und
    „ärzte" blieben zwei Tags.

    Der Fremdschlüssel steht als Dokumentation der Absicht da: SQLite
    erzwingt ihn nur mit `PRAGMA foreign_keys=ON`, und das setzt diese
    Anwendung bewusst nicht. Das Aufräumen beim Löschen eines Dokuments
    erledigt deshalb `delete_document` ausdrücklich.
    """
    _drop_verworfene_tag_tabellen(cursor)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            key TEXT NOT NULL UNIQUE,
            color_index INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS document_tags (
            document_id INTEGER NOT NULL REFERENCES documents (id)
                ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags (id) ON DELETE CASCADE,
            PRIMARY KEY (document_id, tag_id)
        )
        """
    )
    # Die Gegenrichtung: "welche Dokumente hängen an diesem Tag" ist die
    # Abfrage des Filters, der Primärschlüssel deckt nur die andere ab.
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_document_tags_tag
        ON document_tags (tag_id)
        """
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
        relativize_archive_paths(cursor)
        create_indexes(cursor)
        create_tag_tables(cursor)
        # Vor create_fts: der Index liest tags_text aus `documents`, die
        # Spalte muss also schon gefüllt sein, wenn er (neu) gebaut wird.
        backfill_tags_text(cursor)
        create_fts(cursor)

        cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

        conn.commit()


if __name__ == "__main__":
    init_database()

    print("Datenbank initialisiert.")

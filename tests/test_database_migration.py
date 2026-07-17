import sqlite3

from src.database.init_database import init_database


EXPECTED_DOCUMENT_COLUMNS = {
    "id",
    "filename",
    "archive_path",
    "document_type",
    "extracted_data",
    "created_at",
    "verified",
    "document_text",
    "notes",
    "tax_year",
    "content_hash",
    "tax_relevant",
}


def write_test_config(tmp_path, db_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "database:",
                f"  path: {db_path}",
            ]
        ),
        encoding="utf-8",
    )


def get_document_columns(db_path):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("PRAGMA table_info(documents)").fetchall()

    return {row[1] for row in rows}


def test_init_database_creates_current_documents_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "database" / "buerokrator.db"
    write_test_config(tmp_path, db_path)
    monkeypatch.chdir(tmp_path)

    init_database()

    assert get_document_columns(db_path) == EXPECTED_DOCUMENT_COLUMNS


def test_init_database_migrates_old_documents_schema_without_losing_rows(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "database" / "buerokrator.db"
    db_path.parent.mkdir()
    write_test_config(tmp_path, db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                archive_path TEXT,
                document_type TEXT,
                extracted_data TEXT,
                created_at TEXT,
                verified INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO documents (
                filename,
                archive_path,
                document_type,
                extracted_data,
                created_at,
                verified
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "old.pdf",
                "archive/2026/Rechnungen/old.pdf",
                "invoice",
                "{}",
                "2026-06-30T20:00:00",
                0,
            ),
        )

    monkeypatch.chdir(tmp_path)

    init_database()

    assert get_document_columns(db_path) == EXPECTED_DOCUMENT_COLUMNS

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                filename,
                archive_path,
                document_type,
                document_text,
                notes
            FROM documents
            """
        ).fetchone()

    assert row == (
        "old.pdf",
        "archive/2026/Rechnungen/old.pdf",
        "invoice",
        None,
        None,
    )


def test_init_database_sets_schema_version_on_fresh_db(tmp_path, monkeypatch):
    from src.database.init_database import SCHEMA_VERSION

    db_path = tmp_path / "database" / "buerokrator.db"
    write_test_config(tmp_path, db_path)
    monkeypatch.chdir(tmp_path)

    init_database()

    with sqlite3.connect(db_path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert version == SCHEMA_VERSION
    # Frische DB: kein Backup nötig.
    assert not list(db_path.parent.glob("pre_migration_*"))


def test_init_database_backs_up_existing_db_before_migration(tmp_path, monkeypatch):
    from src.database.init_database import SCHEMA_VERSION

    db_path = tmp_path / "database" / "buerokrator.db"
    db_path.parent.mkdir()
    write_test_config(tmp_path, db_path)

    # Bestands-DB von vor der Versionierung (user_version 0, alte Spalten).
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT)")
        conn.execute("INSERT INTO documents (filename) VALUES ('alt.pdf')")

    monkeypatch.chdir(tmp_path)

    init_database()

    backups = list(db_path.parent.glob("pre_migration_v0_zu_v*_*.db"))
    assert len(backups) == 1

    # Das Backup enthält den Stand VOR der Migration (alte Spalten, Daten da).
    with sqlite3.connect(backups[0]) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(documents)")}
        row = conn.execute("SELECT filename FROM documents").fetchone()

    assert columns == {"id", "filename"}
    assert row == ("alt.pdf",)

    with sqlite3.connect(db_path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert version == SCHEMA_VERSION


def test_init_database_indexes_existing_rows_in_fts(tmp_path, monkeypatch):
    # Migration einer Bestands-DB (v1, ohne FTS): der Volltextindex wird
    # angelegt UND mit dem Bestand befüllt (rebuild).
    db_path = tmp_path / "database" / "buerokrator.db"
    db_path.parent.mkdir()
    write_test_config(tmp_path, db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                document_text TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO documents (filename, document_text) VALUES (?, ?)",
            ("bestand.pdf", "Inhalt aus dem Altbestand"),
        )
        conn.execute("PRAGMA user_version = 1")

    monkeypatch.chdir(tmp_path)

    init_database()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT rowid FROM documents_fts
            WHERE documents_fts MATCH '"Altbestand"'
            """
        ).fetchall()

    assert rows == [(1,)]


def test_init_database_skips_backup_when_version_is_current(tmp_path, monkeypatch):
    db_path = tmp_path / "database" / "buerokrator.db"
    write_test_config(tmp_path, db_path)
    monkeypatch.chdir(tmp_path)

    init_database()
    init_database()  # zweiter Start: Version aktuell, kein Backup

    assert not list(db_path.parent.glob("pre_migration_*"))


def test_init_database_rejects_newer_schema_version(tmp_path, monkeypatch):
    import pytest

    from src.database.init_database import SCHEMA_VERSION

    db_path = tmp_path / "database" / "buerokrator.db"
    db_path.parent.mkdir()
    write_test_config(tmp_path, db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")

    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="Schemaversion"):
        init_database()

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

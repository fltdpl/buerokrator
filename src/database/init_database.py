from src.database.database import get_connection


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

    return {row[1] for row in rows}


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


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

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

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_database()

    print("Datenbank initialisiert.")

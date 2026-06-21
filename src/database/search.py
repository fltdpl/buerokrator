from src.database.database import get_connection


def search_documents(search_term):

    conn = get_connection()

    cursor = conn.cursor()

    rows = cursor.execute(
        """
        SELECT
            id,
            filename,
            archive_path,
            document_type,
            extracted_data,
            verified,
            created_at,
            document_text,
            notes
        FROM documents
        WHERE

            filename LIKE ?
            OR document_type LIKE ?
            OR extracted_data LIKE ?
            OR document_text LIKE ?
            OR notes LIKE ?

        ORDER BY id DESC
        """,
        (
            f"%{search_term}%",
            f"%{search_term}%",
            f"%{search_term}%",
            f"%{search_term}%",
            f"%{search_term}%",
        ),
    ).fetchall()

    conn.close()

    return rows

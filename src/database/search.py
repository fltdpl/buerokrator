from src.database.database import get_connection
from src.database.list_documents import _DOCUMENT_FIELDS


def search_documents(search_term):

    conn = get_connection()

    cursor = conn.cursor()

    rows = cursor.execute(
        f"""
        SELECT {_DOCUMENT_FIELDS}
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

    return [dict(row) for row in rows]

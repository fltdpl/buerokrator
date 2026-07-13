from src.database.database import open_connection
from src.database.list_documents import _DOCUMENT_FIELDS


def search_documents(search_term):

    with open_connection() as conn:
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

    return [dict(row) for row in rows]

from src.database.database import get_connection


def get_recent_documents(limit=10):

    conn = get_connection()

    cursor = conn.cursor()

    rows = cursor.execute(
        """
        SELECT
            id,
            filename,
            document_type,
            created_at
        FROM documents
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return rows

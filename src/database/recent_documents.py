from src.database.database import open_connection


def get_recent_documents(limit=10):

    with open_connection() as conn:
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

    return [dict(row) for row in rows]

from src.database.database import open_connection


def get_category_counts():
    with open_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            """
            SELECT
                document_type,
                COUNT(*)
            FROM documents
            GROUP BY document_type
            """
        ).fetchall()

    return dict(rows)

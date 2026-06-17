from src.database.database import get_connection


def get_category_counts():
    conn = get_connection()
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
    conn.close()

    return dict(rows)

from src.database.database import get_connection


def get_statistics():

    conn = get_connection()
    cursor = conn.cursor()
    total = cursor.execute(
        """
        SELECT COUNT(*)
        FROM documents
        """
    ).fetchone()[0]

    by_type = cursor.execute(
        """
        SELECT
            document_type,
            COUNT(*)
        FROM documents
        GROUP BY document_type
        """
    ).fetchall()

    conn.close()

    return total, by_type

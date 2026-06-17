from src.database.connection import get_connection


def get_unverified_documents():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM documents
        WHERE verified = 0
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return rows

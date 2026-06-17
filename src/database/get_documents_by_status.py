from src.database.connection import get_connection


def get_documents_by_status(verified):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM documents
        WHERE verified = ?
        ORDER BY id DESC
        """,
        (verified,),
    )

    rows = cursor.fetchall()

    conn.close()

    return rows

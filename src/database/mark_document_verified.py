from src.database.database import get_connection


def mark_document_verified(document_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE documents
        SET verified = 1
        WHERE id = ?
        """,
        (document_id,),
    )

    conn.commit()

    conn.close()

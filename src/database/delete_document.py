from src.database.database import get_connection


def delete_document(document_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM documents
        WHERE id = ?
        """,
        (document_id,),
    )

    conn.commit()

    conn.close()

from src.database.database import open_connection


def delete_document(document_id):

    with open_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM documents
            WHERE id = ?
            """,
            (document_id,),
        )

        conn.commit()

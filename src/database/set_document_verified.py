from src.database.database import open_connection


def set_document_verified(document_id, verified):
    with open_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE documents
            SET verified = ?
            WHERE id = ?
            """,
            (
                verified,
                document_id,
            ),
        )

        conn.commit()


def mark_document_verified(document_id):
    set_document_verified(document_id, 1)


def mark_document_unverified(document_id):
    set_document_verified(document_id, 0)

from src.database.database import get_connection


def set_document_verified(document_id, verified):
    conn = get_connection()
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
    conn.close()


def mark_document_verified(document_id):
    set_document_verified(document_id, 1)


def mark_document_unverified(document_id):
    set_document_verified(document_id, 0)

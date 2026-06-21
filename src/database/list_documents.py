from src.database.database import get_connection


def list_documents(document_type=None):
    conn = get_connection()
    cursor = conn.cursor()

    if document_type:
        rows = cursor.execute(
            """
            SELECT
                id,
                filename,
                archive_path,
                document_type,
                extracted_data,
                verified,
                created_at,
                document_text,
                notes
            FROM documents
            WHERE document_type = ?
            ORDER BY id DESC
            """,
            (document_type,),
        ).fetchall()

    else:
        rows = cursor.execute(
            """
            SELECT
                id,
                filename,
                archive_path,
                document_type,
                extracted_data,
                verified,
                created_at,
                document_text,
                notes
            FROM documents
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()

    return rows


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

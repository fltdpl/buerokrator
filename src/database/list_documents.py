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
                verified
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
                verified
            FROM documents
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()

    return rows

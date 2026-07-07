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


def get_document(document_id):
    if document_id is None:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute(
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
        WHERE id = ?
        """,
        (document_id,),
    ).fetchone()

    conn.close()

    return row


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


def get_next_unverified_id(exclude_id=None):
    """Liefert die ID des nächsten ungeprüften Dokuments (oder None).

    Aufsteigend nach ID, damit der Prüf-Workflow eine stabile Reihenfolge
    hat; exclude_id blendet das gerade bearbeitete Dokument aus.
    """
    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute(
        """
        SELECT id
        FROM documents
        WHERE verified = 0 AND id != ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (exclude_id if exclude_id is not None else -1,),
    ).fetchone()

    conn.close()

    return row[0] if row else None


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

from src.database.database import get_connection

# Spalten, die die Dokument-Konsumenten (Services, Frontend, Export) erwarten.
# Zugriff erfolgt per Name (dict), die Reihenfolge hier ist nur kosmetisch.
_DOCUMENT_FIELDS = """
    id,
    filename,
    archive_path,
    document_type,
    extracted_data,
    verified,
    created_at,
    document_text,
    notes,
    tax_relevant
"""


def list_documents(document_type=None):
    conn = get_connection()
    cursor = conn.cursor()

    if document_type:
        rows = cursor.execute(
            f"""
            SELECT {_DOCUMENT_FIELDS}
            FROM documents
            WHERE document_type = ?
            ORDER BY id DESC
            """,
            (document_type,),
        ).fetchall()

    else:
        rows = cursor.execute(
            f"""
            SELECT {_DOCUMENT_FIELDS}
            FROM documents
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def get_document(document_id):
    if document_id is None:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute(
        f"""
        SELECT {_DOCUMENT_FIELDS}
        FROM documents
        WHERE id = ?
        """,
        (document_id,),
    ).fetchone()

    conn.close()

    return dict(row) if row is not None else None


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

    return row["id"] if row else None

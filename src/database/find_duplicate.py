from src.database.database import get_connection


def find_document_by_hash(content_hash):
    """(id, filename) des Dokuments mit diesem Inhalts-Hash — oder None.

    NULL-Hashes (Altbestand vor der Dubletten-Erkennung) matchen nie.
    """
    if not content_hash:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute(
        """
        SELECT id, filename
        FROM documents
        WHERE content_hash = ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (content_hash,),
    ).fetchone()

    conn.close()

    return (row["id"], row["filename"]) if row is not None else None

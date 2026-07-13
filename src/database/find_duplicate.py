from src.database.database import open_connection


def find_document_by_hash(content_hash):
    """(id, filename) des Dokuments mit diesem Inhalts-Hash — oder None.

    NULL-Hashes (Altbestand vor der Dubletten-Erkennung) matchen nie.
    """
    if not content_hash:
        return None

    with open_connection() as conn:
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

    return (row["id"], row["filename"]) if row is not None else None

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


def list_duplicate_candidates(exclude_id):
    """Alle Dokumente außer einem — nur die für den Inhaltsvergleich nötigen
    Spalten.

    Bewusst NICHT `list_documents()`: das liefert zusätzlich den
    OCR-Volltext jedes Dokuments. Der Vergleich läuft bei jedem Aufruf der
    Detailseite, da darf nicht der halbe Bestand durch den Speicher.
    """
    with open_connection() as conn:
        cursor = conn.cursor()

        rows = cursor.execute(
            """
            SELECT id, filename, document_type, extracted_data
            FROM documents
            WHERE id != ?
            ORDER BY id ASC
            """,
            (exclude_id if exclude_id is not None else -1,),
        ).fetchall()

    return [dict(row) for row in rows]

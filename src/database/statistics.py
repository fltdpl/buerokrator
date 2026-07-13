from src.database.database import open_connection


def get_statistics():

    with open_connection() as conn:
        cursor = conn.cursor()
        total = cursor.execute(
            """
            SELECT COUNT(*)
            FROM documents
            """
        ).fetchone()[0]

        by_type = cursor.execute(
            """
            SELECT
                document_type,
                COUNT(*)
            FROM documents
            GROUP BY document_type
            """
        ).fetchall()

    return total, by_type


def get_verification_statistics():
    """Anzahl (ungeprüft, geprüft) — bewusst ein Tupel, denn alle Aufrufer
    entpacken das Ergebnis."""
    with open_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            """
            SELECT
                verified,
                COUNT(*)
            FROM documents
            GROUP BY verified
            """
        ).fetchall()

    counts = {0: 0, 1: 0}
    for verified, count in rows:
        counts[verified] = count

    return counts[0], counts[1]


def get_unknown_document_count():

    with open_connection() as conn:
        cursor = conn.cursor()

        count = cursor.execute(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE document_type = 'unknown'
            """
        ).fetchone()[0]

    return count

"""Lesezugriff auf den geprüften Bestand für das Aussteller-Gedächtnis.

Ausschließlich `verified = 1`: ungeprüfte Dokumente tragen möglicherweise
einen Erkennungsfehler, und ein Gedächtnis, das aus Fehlern lernt, verfestigt
sie. Dieselbe Begründung wie bei der Qualitätsmessung, die ebenfalls nur
geprüfte Dokumente als Ground Truth nimmt.

Ohne Dokumenttext: gebraucht werden nur Typ und erkannte Werte, und der Text
macht den Löwenanteil der Zeilengröße aus.
"""

from src.database.database import open_connection


def list_verified_summaries():
    """Geprüfte Dokumente ohne Text: id, document_type, extracted_data."""
    with open_connection() as conn:
        rows = conn.cursor().execute(
            """
            SELECT id, document_type, extracted_data
            FROM documents
            WHERE verified = 1
            """
        ).fetchall()

    return [dict(row) for row in rows]

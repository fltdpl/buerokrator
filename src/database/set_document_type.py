from src.database.database import get_connection


def set_document_type(document_id, document_type):
    """Ändert den Dokumenttyp und setzt das Dokument auf ungeprüft zurück.

    Bewusst nicht über update_document: die setzt verified = 1. Nach einem
    Typwechsel gelten andere Felder, das Dokument gehört erneut in den
    Prüf-Workflow.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE documents
        SET document_type = ?, verified = 0
        WHERE id = ?
        """,
        (document_type, document_id),
    )

    conn.commit()
    conn.close()

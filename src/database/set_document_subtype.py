import json

from src.database.database import get_connection


def set_document_subtype(document_id, subtype):
    """Setzt den Subtyp (document_subtype) und markiert das Dokument ungeprüft.

    Ändert nur `document_subtype` in den extrahierten Daten; die übrigen Felder
    bleiben unangetastet (die Whitelist greift erst beim nächsten Speichern im
    Prüf-Workflow, damit hier nichts verloren geht). Wie beim Typwechsel wird
    verified = 0 gesetzt, weil ein anderer Subtyp andere Felder gültig macht.

    Gibt True zurück, wenn ein Dokument geändert wurde.
    """
    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT extracted_data FROM documents WHERE id = ?",
        (document_id,),
    ).fetchone()

    if row is None:
        conn.close()
        return False

    try:
        data = json.loads(row["extracted_data"] or "{}")

    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data["document_subtype"] = subtype

    cursor.execute(
        """
        UPDATE documents
        SET extracted_data = ?, verified = 0
        WHERE id = ?
        """,
        (json.dumps(data, ensure_ascii=False), document_id),
    )

    conn.commit()
    conn.close()

    return True

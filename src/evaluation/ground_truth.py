import json

from src.core.document_fields import whitelist_fields
from src.database.database import open_connection


def load_ground_truth(document_type=None, limit=None):
    """Lädt Ground-Truth-Fälle aus der Datenbank.

    Grundlage sind alle als geprüft markierten Dokumente (verified = 1) mit
    gespeichertem Dokumenttext: die in der App korrigierten Felder gelten als
    Sollwerte, der gespeicherte OCR-Text als Eingabe. Gemessen wird damit
    Klassifikation + Extraktion — nicht die OCR-Qualität selbst.
    """
    query = """
        SELECT id, filename, document_type, extracted_data, document_text
        FROM documents
        WHERE verified = 1
          AND document_text IS NOT NULL
          AND length(document_text) > 0
    """
    params = []
    if document_type:
        query += " AND document_type = ?"
        params.append(document_type)
    query += " ORDER BY id"
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with open_connection() as conn:
        rows = conn.cursor().execute(query, params).fetchall()

    cases = []
    for doc_id, filename, doc_type, extracted_data, document_text in rows:
        try:
            fields = json.loads(extracted_data) if extracted_data else {}
        except json.JSONDecodeError:
            fields = {}

        if not isinstance(fields, dict):
            fields = {}

        # Altbestände können Felder enthalten, die die heutige Pipeline per
        # Whitelist gar nicht mehr ausgibt — die würden sonst unfair als
        # "fehlend" zählen. Sollwerte deshalb durch dieselbe Whitelist filtern.
        fields = whitelist_fields(doc_type, fields)

        cases.append(
            {
                "name": f"#{doc_id} {filename}",
                "file": filename,
                "document_type": doc_type,
                "fields": fields,
                "document_text": document_text,
                "verified": True,
            }
        )

    return cases

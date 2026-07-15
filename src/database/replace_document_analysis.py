import json

from src.database.database import open_connection
from src.organizer.date_utils import extract_year


def replace_document_analysis(document_id, document_type, extracted_data):
    """Ersetzt das Analyse-Ergebnis eines Dokuments und widerruft die Freigabe.

    Für „Erneut prüfen": Typ und extracted_data kommen aus einer frischen
    Klassifikation/Extraktion, das Dokument gehört danach wieder in den
    Prüf-Workflow (verified = 0). Der tax_relevant-Override wird auf NULL
    zurückgesetzt, damit der Default des (ggf. neuen) Typs/Subtyps greift.

    Bewusst nicht über update_document: die setzt verified = 1 und behielte
    den Override. Datei/Pfad bleiben unangetastet.
    """
    with open_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE documents
            SET
                document_type = ?,
                extracted_data = ?,
                verified = 0,
                tax_year = ?,
                tax_relevant = NULL
            WHERE id = ?
            """,
            (
                document_type,
                json.dumps(extracted_data, ensure_ascii=False),
                extract_year(extracted_data),
                document_id,
            ),
        )

        conn.commit()

        return cursor.rowcount > 0

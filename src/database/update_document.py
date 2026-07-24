import json

from src.database.database import open_connection
from src.organizer.date_utils import extract_year


def update_document(
    document_id,
    filename,
    archive_path,
    document_type,
    extracted_data,
    notes="",
    tax_relevant=None,
    tax_purpose=None,
):

    with open_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE documents
            SET
                filename = ?,
                archive_path = ?,
                document_type = ?,
                extracted_data = ?,
                notes = ?,
                verified = 1,
                tax_year = ?,
                tax_relevant = ?,
                tax_purpose = ?
            WHERE id = ?
            """,
            (
                filename,
                archive_path,
                document_type,
                json.dumps(
                    extracted_data,
                    ensure_ascii=False,
                ),
                notes,
                extract_year(extracted_data),
                None if tax_relevant is None else int(bool(tax_relevant)),
                tax_purpose or None,
                document_id,
            ),
        )

        conn.commit()


def update_document_data(document_id, extracted_data):
    """Ersetzt NUR extracted_data (z. B. Aussteller-Vereinheitlichung).

    Lässt im Gegensatz zu update_document (setzt verified = 1, benennt um)
    und replace_document_analysis (widerruft die Freigabe) den Prüfstatus,
    die Datei und die Notizen unangetastet — für reine Metadaten-Korrekturen
    ohne inhaltliche Neubewertung.
    """
    with open_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE documents
            SET extracted_data = ?, tax_year = ?
            WHERE id = ?
            """,
            (
                json.dumps(extracted_data, ensure_ascii=False),
                extract_year(extracted_data),
                document_id,
            ),
        )

        conn.commit()

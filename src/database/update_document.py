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

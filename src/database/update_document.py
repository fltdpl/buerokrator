import json

from src.database.database import get_connection
from src.organizer.date_utils import extract_year


def update_document(
    document_id,
    filename,
    archive_path,
    document_type,
    extracted_data,
    notes="",
):

    conn = get_connection()

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
            tax_year = ?
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
            document_id,
        ),
    )

    conn.commit()

    conn.close()

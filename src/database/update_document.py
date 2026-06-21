import json

from src.database.database import get_connection


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
            verified = ?
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
            document_id,
        ),
    )

    conn.commit()

    conn.close()

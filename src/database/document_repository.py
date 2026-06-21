import json
from datetime import datetime

from src.database.database import get_connection


def insert_document(
    filename,
    archive_path,
    document_type,
    extracted_data,
    document_text=None,
):

    conn = get_connection()
    cursor = conn.cursor()

    verified = 0

    cursor.execute(
        """
        INSERT INTO documents (

            filename,
            archive_path,
            document_type,
            extracted_data,
            document_text,
            created_at,
            verified

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            filename,
            archive_path,
            document_type,
            json.dumps(
                extracted_data,
                ensure_ascii=False,
            ),
            document_text,
            datetime.now().isoformat(),
            verified,
        ),
    )

    conn.commit()

    conn.close()

import json
from datetime import datetime

from src.database.database import get_connection
from src.database.update_document import update_document
from src.organizer.filename_builder import rename_document


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


def save_document(
    document_id,
    archive_path,
    document_type,
    extracted_data,
    notes="",
):

    new_path = rename_document(
        archive_path,
        document_type,
        extracted_data,
    )

    update_document(
        document_id=document_id,
        filename=new_path.name,
        archive_path=str(new_path),
        document_type=document_type,
        extracted_data=extracted_data,
        notes=notes,
    )

    return new_path


def update_notes(
    document_id,
    notes,
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE documents
        SET notes = ?
        WHERE id = ?
        """,
        (
            notes,
            document_id,
        ),
    )

    conn.commit()
    conn.close()

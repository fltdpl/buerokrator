import json
from datetime import datetime

from src.core.amount_utils import enforce_amount_signs
from src.core.document_fields import whitelist_fields
from src.database.database import get_connection
from src.database.update_document import update_document
from src.organizer.date_utils import extract_year
from src.organizer.filename_builder import rename_document
from src.tax.tax_relevance import default_tax_relevance


def insert_document(
    filename,
    archive_path,
    document_type,
    extracted_data,
    document_text=None,
    content_hash=None,
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
            verified,
            tax_year,
            content_hash,
            tax_relevant

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            extract_year(extracted_data),
            content_hash,
            int(default_tax_relevance(document_type, extracted_data)),
        ),
    )

    document_id = cursor.lastrowid

    conn.commit()

    conn.close()

    return document_id


def save_document(
    document_id,
    archive_path,
    document_type,
    extracted_data,
    notes="",
    tax_relevant=None,
):

    # Auf die für den Dokumenttyp erlaubten Felder begrenzen, damit auch beim
    # Bearbeiten keine fremden Felder (weiter-)gespeichert werden. Beträge als
    # Magnitude speichern (Vorzeichen-Verwechslung absichern).
    extracted_data = enforce_amount_signs(
        whitelist_fields(document_type, extracted_data)
    )

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
        tax_relevant=tax_relevant,
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

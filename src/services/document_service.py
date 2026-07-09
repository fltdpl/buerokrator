"""Framework-neutrale Dokument-Operationen für die GUI-Schicht.

Nimmt und liefert nur Plain Data (dicts/Listen) — kein Streamlit/NiceGUI,
kein Session-State. Frontends verdrahten hier nur noch Events.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from src.core.document_display import get_document_display_name
from src.database.delete_document import delete_document
from src.database.list_documents import get_document
from src.organizer.date_utils import year_from_archive_path
from src.organizer.filename_builder import get_unique_target_path

TRASH_DIR = Path("trash")


def parse_document_row(row):
    """DB-Zeile -> dict mit geparsten extracted_data (robust gegen kaputtes JSON)."""
    try:
        data = json.loads(row[4])

        if not isinstance(data, dict):
            data = {}

    except Exception:
        data = {}

    return {
        "id": row[0],
        "filename": row[1],
        "archive_path": row[2],
        "document_type": row[3],
        "data": data,
        "verified": bool(row[5]),
        "created_at": row[6],
        "document_text": row[7] if len(row) > 7 else "",
        "notes": row[8] if len(row) > 8 else "",
    }


def move_document_to_trash(document_id, trash_dir=TRASH_DIR):
    """Löscht ein Dokument aus der DB und verschiebt das PDF in den Papierkorb.

    Bewusst KEIN endgültiges Löschen: ein Fehlklick darf kein
    Original-Dokument vernichten. Gibt den Papierkorb-Pfad zurück
    (None, wenn die Archivdatei fehlte).
    """
    row = get_document(document_id)

    if row is None:
        return None

    source = Path(row[2])
    trashed_path = None

    if source.exists():
        trash = Path(trash_dir)
        trash.mkdir(parents=True, exist_ok=True)
        target = get_unique_target_path(trash / source.name)
        shutil.move(str(source), str(target))
        trashed_path = target

    delete_document(document_id)

    return trashed_path


def document_year(row):
    return year_from_archive_path(row[2])


def filter_documents(
    documents,
    document_type=None,
    verified=None,
    from_year=None,
    to_year=None,
    issuer=None,
    filename=None,
):
    """Wendet die Listen-Filter an (alle optional, None = kein Filter)."""
    if document_type:
        documents = [row for row in documents if row[3] == document_type]

    if verified is not None:
        documents = [row for row in documents if bool(row[5]) == verified]

    if from_year is not None and to_year is not None and from_year > to_year:
        from_year, to_year = to_year, from_year

    if from_year is not None or to_year is not None:
        lower = from_year if from_year is not None else float("-inf")
        upper = to_year if to_year is not None else float("inf")

        documents = [
            row
            for row in documents
            if (year := document_year(row)) is not None and lower <= year <= upper
        ]

    if issuer:
        needle = issuer.lower().strip()
        filtered = []

        for row in documents:
            data = parse_document_row(row)["data"]
            value = data.get("issuer") or data.get("insurer") or ""

            if needle in value.lower():
                filtered.append(row)

        documents = filtered

    if filename:
        needle = filename.lower().strip()
        documents = [row for row in documents if needle in row[1].lower()]

    return documents


def available_years(documents):
    return sorted(
        {
            year
            for year in (document_year(row) for row in documents)
            if year is not None
        }
    )


def _format_file_size(path):
    try:
        size = Path(path).stat().st_size

    except OSError:
        return "-"

    if size < 1024:
        return f"{size} B"

    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"

    return f"{size / 1024 / 1024:.1f} MB"


def _format_created_at(created_at):
    try:
        return datetime.fromisoformat(str(created_at).replace("Z", "")).strftime(
            "%d.%m.%Y"
        )

    except Exception:
        return "-"


def build_table_rows(documents):
    """Anzeigezeilen der Dokumentenliste (inkl. Betrag/Aussteller-Rohwerten)."""
    rows = []

    for row in documents:
        document = parse_document_row(row)
        data = document["data"]
        year = document_year(row)

        rows.append(
            {
                "id": document["id"],
                "verified": document["verified"],
                "year": year,
                "display_name": get_document_display_name(
                    document["document_type"],
                    data,
                    year=year,
                ),
                "document_type": document["document_type"],
                "issuer": data.get("issuer") or data.get("insurer") or "",
                "amount": data.get("amount"),
                "created_at": _format_created_at(document["created_at"]),
                "file_size": _format_file_size(document["archive_path"]),
            }
        )

    return rows

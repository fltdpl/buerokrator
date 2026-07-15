"""Framework-neutrale Dokument-Operationen für die GUI-Schicht.

Nimmt und liefert nur Plain Data (dicts/Listen) — kein Streamlit/NiceGUI,
kein Session-State. Frontends verdrahten hier nur noch Events.
"""

import json
from datetime import datetime
from pathlib import Path

from src.core.document_display import (
    get_document_art_label,
    get_document_display_name,
)
from src.database.delete_document import delete_document
from src.database.list_documents import get_document
from src.database.set_document_subtype import set_document_subtype
from src.database.set_document_type import set_document_type
from src.organizer.date_utils import year_from_archive_path
from src.organizer.trash import move_to_trash


def parse_document_row(row):
    """DB-Zeile -> dict mit geparsten extracted_data (robust gegen kaputtes JSON)."""
    try:
        data = json.loads(row["extracted_data"])

        if not isinstance(data, dict):
            data = {}

    except Exception:
        data = {}

    return {
        "id": row["id"],
        "filename": row["filename"],
        "archive_path": row["archive_path"],
        "document_type": row["document_type"],
        "data": data,
        "verified": bool(row["verified"]),
        "created_at": row["created_at"],
        "document_text": row["document_text"] or "",
        "notes": row["notes"] or "",
        # Rohwert (0/1/None); die effektive Relevanz löst resolve_tax_relevance
        # mit dem Typ/Subtyp-Default auf.
        "tax_relevant": row["tax_relevant"],
    }


def move_document_to_trash(document_id, trash_dir=None):
    """Löscht ein Dokument aus der DB und verschiebt das PDF in den Papierkorb.

    Bewusst KEIN endgültiges Löschen: ein Fehlklick darf kein
    Original-Dokument vernichten. Gibt den Papierkorb-Pfad zurück
    (None, wenn die Archivdatei fehlte).

    Reihenfolge bewusst Datei-zuerst (nicht atomar): bricht es zwischen den
    Schritten ab, zeigt die DB ein Dokument mit fehlender Archivdatei — das
    fällt in der App sofort auf und die Datei liegt auffindbar im Papierkorb.
    Umgekehrt (DB zuerst) entstünde eine unsichtbare Waisen-Datei im Archiv.
    Sichtbarer Defekt schlägt unsichtbaren.
    """
    row = get_document(document_id)

    if row is None:
        return None

    trashed_path = move_to_trash(row["archive_path"], trash_dir=trash_dir)

    delete_document(document_id)

    return trashed_path


def move_documents_to_trash(document_ids, trash_dir=None):
    """Mehrere Dokumente in den Papierkorb; liefert die Anzahl gelöschter Einträge.

    Gezählt wird der gelöschte DB-Eintrag, nicht die verschobene Datei: fehlt
    das Archiv-PDF bereits, ist das Dokument trotzdem gelöscht.
    """
    deleted = 0

    for document_id in document_ids:
        if get_document(document_id) is None:
            continue

        move_document_to_trash(document_id, trash_dir=trash_dir)
        deleted += 1

    return deleted


def reclassify_documents(document_ids, document_type):
    """Setzt den Dokumenttyp mehrerer Dokumente und markiert sie als ungeprüft.

    Ungeprüft, weil ein Typwechsel andere Felder gültig macht: die Extraktion
    muss von Hand nachgezogen werden. Die Datei wird NICHT umbenannt oder
    verschoben — das passiert beim nächsten Speichern im Prüf-Workflow.
    """
    changed = 0

    for document_id in document_ids:
        if get_document(document_id) is None:
            continue

        set_document_type(document_id, document_type)
        changed += 1

    return changed


def set_documents_subtype(document_ids, subtype):
    """Setzt den Subtyp (Unterart) mehrerer Dokumente, markiert sie ungeprüft.

    Für die Umsortierung von Bestandsdokumenten (z. B. viele gleichartige
    SV-Meldungen auf einen eigenen Subtyp). Ändert nur die Unterart; die
    Whitelist greift erst beim nächsten Speichern.
    """
    changed = 0

    for document_id in document_ids:
        if set_document_subtype(document_id, subtype):
            changed += 1

    return changed


def document_year(row):
    return year_from_archive_path(row["archive_path"])


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
        documents = [row for row in documents if row["document_type"] == document_type]

    if verified is not None:
        documents = [row for row in documents if bool(row["verified"]) == verified]

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
        documents = [row for row in documents if needle in row["filename"].lower()]

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
                "art_label": get_document_art_label(
                    document["document_type"],
                    data,
                ),
                "document_type": document["document_type"],
                "issuer": (
                    data.get("issuer")
                    or data.get("insurer")
                    or data.get("employer")
                    or ""
                ),
                "amount": data.get("amount"),
                "created_at": _format_created_at(document["created_at"]),
                "file_size": _format_file_size(document["archive_path"]),
            }
        )

    return rows

"""Framework-neutrale Kennzahlen für Dashboard/Analyse."""

from pathlib import Path

from src.core.config import load_config
from src.database.list_documents import get_next_unverified_id
from src.database.recent_documents import get_recent_documents
from src.database.statistics import get_statistics, get_verification_statistics
from src.processor.batch_import import find_inbox_documents


def get_archive_size() -> int:
    """Summe der Dateigrößen im Archiv des aktiven Profils, in Bytes.

    Nur der Archivordner — Datenbank, Sicherungen und Papierkorb bleiben
    außen vor. Sie sind keine abgelegten Dokumente, und mitgezählt wäre die
    Zahl nicht mehr erklärbar (der Papierkorb allein kann sie verdoppeln).
    Der Pfad kommt aus der Config und ist damit automatisch profilbezogen.

    Ohne Cache: ein voller Durchlauf über das echte Archiv liegt im
    Millisekundenbereich, und das Dashboard durchsucht beim Aufbau ohnehin
    schon die Inbox.
    """
    # Fehlt der Schlüssel (von Hand gekürzte Config), ist die Größe schlicht
    # unbekannt — das Dashboard darf daran nicht scheitern.
    konfiguriert = (load_config().get("paths") or {}).get("archive")

    if not konfiguriert:
        return 0

    archiv = Path(konfiguriert)

    if not archiv.exists():
        return 0

    gesamt = 0

    for pfad in archiv.rglob("*"):
        try:
            if pfad.is_file():
                gesamt += pfad.stat().st_size

        except OSError:
            # Eine unlesbare Datei darf das Dashboard nicht scheitern lassen.
            continue

    return gesamt


def get_dashboard_data():
    """Alle Dashboard-Kennzahlen in einem Aufruf (Plain Data)."""
    total, by_type = get_statistics()
    unverified_count, verified_count = get_verification_statistics()

    return {
        "total": total,
        "counts_by_type": dict(by_type),
        "unverified_count": unverified_count,
        "verified_count": verified_count,
        "inbox_count": len(find_inbox_documents()),
        "first_unverified_id": get_next_unverified_id(),
        "recent": get_recent_documents(),
        "archive_size": get_archive_size(),
    }

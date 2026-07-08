"""Framework-neutrale Kennzahlen für Dashboard/Analyse."""

from src.database.list_documents import get_next_unverified_id
from src.database.recent_documents import get_recent_documents
from src.database.statistics import get_statistics, get_verification_statistics
from src.processor.batch_import import find_inbox_documents


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
    }

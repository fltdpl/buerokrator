import re
from datetime import datetime


def normalize_date(date_string):

    try:
        return datetime.strptime(date_string, "%d.%m.%Y").strftime("%Y-%m-%d")

    except Exception:
        return date_string


def _year_from_value(value):
    if value is None:
        return None

    match = re.search(r"(?:19|20)\d{2}", str(value))
    if match:
        return match.group(0)

    return None


def extract_year(extracted_data, fallback_year=None):
    """Ermittelt das Dokumentjahr aus den extrahierten Daten.

    Reihenfolge: tax_year, document_date. Fällt auf fallback_year zurück
    (Standard: aktuelles Jahr), wenn kein plausibles Jahr gefunden wird.
    """
    if fallback_year is None:
        fallback_year = str(datetime.now().year)

    if not isinstance(extracted_data, dict):
        return fallback_year

    for key in ("tax_year", "document_date"):
        year = _year_from_value(extracted_data.get(key))
        if year:
            return year

    return fallback_year

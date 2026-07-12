import re
from datetime import datetime
from pathlib import Path


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

    Reihenfolge: tax_year, document_date, period_start. Fällt auf
    fallback_year zurück (Standard: aktuelles Jahr), wenn kein plausibles Jahr
    gefunden wird.
    """
    if fallback_year is None:
        fallback_year = str(datetime.now().year)

    if not isinstance(extracted_data, dict):
        return fallback_year

    for key in ("tax_year", "document_date", "period_start"):
        year = _year_from_value(extracted_data.get(key))
        if year:
            return year

    return fallback_year


def normalize_month(month):
    """Normalisiert eine Monatsangabe zu zweistellig (z. B. 3 -> "03").

    Gibt "00" als Platzhalter zurück, wenn kein Monat erkennbar ist, damit
    Dateinamen im Format YYYY-MM korrekt sortieren.
    """
    if month is None:
        return "00"

    text = str(month).strip()

    if text.isdigit():
        return f"{int(text):02d}"

    return text or "00"


def year_from_archive_path(archive_path):
    """Liest das Archivjahr aus dem Pfad (Konvention archive/<Jahr>/...).

    Gibt das Jahr als int zurück oder None, wenn kein plausibles Jahr im Pfad
    enthalten ist.
    """
    archive_path = archive_path or ""

    for part in Path(archive_path).parts:
        if re.fullmatch(r"(?:19|20)\d{2}", part):
            return int(part)

    match = re.search(r"(?:19|20)\d{2}", str(archive_path))
    if match:
        return int(match.group(0))

    return None

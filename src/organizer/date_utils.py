import re
from datetime import datetime
from pathlib import Path


# Rein numerische Formate, in Reihenfolge der Eindeutigkeit. "%d/%m/%Y" fehlt
# BEWUSST: "01/03/2024" ist zwischen deutschem und US-Format mehrdeutig — ein
# still falsch geratenes Datum wäre schlimmer als ein unschöner Dateiname
# (die Pfadsicherheit übernimmt filename_builder._safe_filename).
_NUMERISCHE_FORMATE = ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d")

# Deutsche Monatsnamen samt gängiger Abkürzungen. Eigene Tabelle statt
# locale-abhängigem "%B": die Locale des Zielsystems ist nicht steuerbar.
_MONATSNAMEN = {
    "januar": 1, "jan": 1,
    "februar": 2, "feb": 2,
    "märz": 3, "maerz": 3, "mrz": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mai": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}

# "20. April 2017", "1. Januar 2017", "20 Apr. 2017". Der Monatsname wird als
# GANZES Wort gefasst und danach nachgeschlagen — sonst schlüge die Erkennung
# auf Teilwörtern an ("Mai" in "Mailand").
_TEXT_DATUM = re.compile(
    r"^(\d{1,2})\.?\s+([A-Za-zÄÖÜäöüß]+)\.?\s+(\d{4})$"
)


def _parse_textdatum(text):
    match = _TEXT_DATUM.match(text)

    if match is None:
        return None

    monat = _MONATSNAMEN.get(match.group(2).casefold())

    if monat is None:
        return None

    try:
        return datetime(int(match.group(3)), monat, int(match.group(1)))

    except ValueError:
        # z. B. "31. Februar 2020"
        return None


def _parse_datum(text):
    """Versteht deutsches Voll-/Kurzformat, ISO und ausgeschriebene Monate."""
    for date_format in _NUMERISCHE_FORMATE:
        try:
            return datetime.strptime(text, date_format)

        except ValueError:
            continue

    return _parse_textdatum(text)


def to_german_date(date_string):
    """Datum als DD.MM.YYYY — das Format, in dem die App Datumsfelder führt.

    Gegenstück zu normalize_date: ISO ist die interne Form für Dateinamen und
    Vergleiche, DD.MM.YYYY die Form im Datensatz und im Formular. Beide
    verstehen dieselben Schreibweisen; unparsbare Werte kommen unverändert
    zurück, damit ein unverstandenes Datum nichts abbricht.
    """
    if not isinstance(date_string, str):
        return date_string

    text = date_string.strip()

    if not text:
        return date_string

    parsed = _parse_datum(text)

    return parsed.strftime("%d.%m.%Y") if parsed else date_string


def normalize_date(date_string):
    """Datum als YYYY-MM-DD; unparsbare Werte kommen unverändert zurück.

    Versteht das deutsche Vollformat, zweistellige Jahre ("20.06.18") und
    ausgeschriebene Monate ("20. April 2017"). Die beiden letzten fehlten und
    schlugen doppelt durch: der Rohwert landete im Dateinamen UND
    `extract_year` fand kein Jahr, sodass das Dokument im Ordner des
    Importjahres statt des Dokumentjahres archiviert wurde.

    Rohwert-Rückgabe ist Absicht: ein unverstandenes Datum darf den
    Dateinamen-Bau nicht abbrechen.
    """
    if not isinstance(date_string, str):
        return date_string

    text = date_string.strip()

    if not text:
        return date_string

    parsed = _parse_datum(text)

    return parsed.strftime("%Y-%m-%d") if parsed else date_string


def _year_from_value(value):
    if value is None:
        return None

    # Über normalize_date, damit auch "20.06.18" und "20. April 2017" ihr
    # Jahr hergeben — die Regex allein findet dort keines.
    match = re.search(r"(?:19|20)\d{2}", str(normalize_date(value)))
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

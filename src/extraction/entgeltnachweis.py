"""Regelparser für Entgeltnachweise.

Der Ausdruck zerreißt bei der Textextraktion viele Wörter, aber die
beschrifteten Anker bleiben lesbar: der Titel „Entgeltnachweis für
<Monat> <Jahr>" (Abrechnungszeitraum) sowie die Summenzeilen
„Gesamtbrutto (EBV):" und „Gesetzl. Netto (EBV)".

Wie überall: nur beschriftete Werte lesen, nichts Identifizierendes setzen
(Arbeitgeber bleibt Sache des LLM), bei unbekanntem Layout {}.
"""

import calendar
import re

_MONTHS = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "maerz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}


def _compact(text):
    return re.sub(r"\s+", "", text.lower())


# Titel: „Entgeltnachweis für August 2021" („für" ist je nach Encoding
# unleserlich). Monat/Jahr = Abrechnungszeitraum.
_TITLE = re.compile(
    r"entgeltnachweisf.{0,2}r(" + "|".join(_MONTHS) + r")(\d{4})"
)

# Betrag hinter einem Label auf der kompakten Zeile: „3.136,45".
_AMOUNT = re.compile(r"([\d.]*\d,\d{2})")

_GROSS_LABEL = "gesamtbrutto(ebv)"
_NET_LABEL = "netto(ebv)"


def _to_float(amount):
    return float(amount.replace(".", "").replace(",", "."))


def is_entgeltnachweis(text):
    compact = _compact(text)

    return _TITLE.search(compact) is not None and _GROSS_LABEL in compact


def parse_entgeltnachweis(text):
    """Zeitraum + Brutto/Netto aus den Summenzeilen; unbekanntes Layout {}."""
    compact = _compact(text)
    title = _TITLE.search(compact)

    if title is None or _GROSS_LABEL not in compact:
        return {}

    month_name, year = title.groups()
    month = _MONTHS[month_name]
    last_day = calendar.monthrange(int(year), month)[1]

    fields = {
        "document_subtype": "gehaltsabrechnung",
        "tax_year": year,
        "period_start": f"01.{month:02d}.{year}",
        "period_end": f"{last_day}.{month:02d}.{year}",
    }

    for field, label in (("gross_amount", _GROSS_LABEL), ("net_amount", _NET_LABEL)):
        # Erste Fundstelle: die Summenzeile der Abrechnung (die Jahressummen
        # weiter unten tragen andere Labels).
        position = compact.find(label)

        if position < 0:
            continue

        match = _AMOUNT.search(compact, position, position + len(label) + 24)

        if match:
            fields[field] = _to_float(match.group(1))

    return fields

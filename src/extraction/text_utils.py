"""Gemeinsame Textwerkzeuge der Regelparser."""

import re

# Beträge der Buchungstabelle tragen ein nachgestelltes + oder -. Genau daran
# unterscheiden sie sich von den Zahlen im Textteil daneben ("Bausparsumme:
# 100.000 EUR", "Freistellungsbetrag: 0,00 EUR").
SIGNED_AMOUNT = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*([+-])")

ANY_AMOUNT = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")

# Der Betrag steht auf der Label-Zeile oder — bei umbrochenem Layout — auf
# einer der beiden folgenden.
_LOOKAHEAD_LINES = 2


def to_float(text):
    """Deutsche Betragsschreibweise (1.234,56) als float."""
    return float(text.replace(".", "").replace(",", "."))


def signed_amounts(text):
    """Alle vorzeichenbehafteten Beträge in Dokumentreihenfolge."""
    return [to_float(match.group(1)) for match in SIGNED_AMOUNT.finditer(text)]


def amount_near(lines, index):
    """Erster Betrag auf der Zeile `index` oder den beiden folgenden."""
    for line in lines[index : index + 1 + _LOOKAHEAD_LINES]:
        match = ANY_AMOUNT.search(line)
        if match:
            return to_float(match.group(1))
    return None

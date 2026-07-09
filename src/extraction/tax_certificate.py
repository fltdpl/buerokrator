"""Steuerbescheinigung über Kapitalerträge — anbieterunabhängig.

Die Beschriftungen dieses Formulars sind nach § 45a EStG amtlich
vorgeschrieben; jede Bank, jeder Broker und jede Bausparkasse druckt sie
wortgleich. Deshalb ist das Formular regelbasiert zuverlässiger lesbar als
per LLM: gemma3:4b ordnet die Betragsspalte reproduzierbar um eine Zeile
versetzt zu (die Kapitalertragsteuer landet als Zinsertrag).

Gelesen werden ausschließlich die vier Betragsfelder. Aussteller, Produkt
und Datum bleiben beim LLM — sie unterscheiden sich je Anbieter und dürfen
nicht aus einem Formularmuster geraten werden.
"""

import re

from src.extraction.text_utils import amount_near

# Reihenfolge zählt: "Kirchensteuer zur Kapitalertragsteuer" muss vor
# "Kapitalertragsteuer" geprüft werden, sonst frisst das kürzere Muster die
# Kirchensteuerzeile.
_LABELS = (
    ("interest", re.compile(r"Höhe der Kapitalerträge", re.IGNORECASE)),
    ("church_tax", re.compile(r"Kirchensteuer", re.IGNORECASE)),
    ("capital_gains_tax", re.compile(r"Kapitalertrags?steuer", re.IGNORECASE)),
    ("soli", re.compile(r"Solidaritätszuschlag", re.IGNORECASE)),
)


def is_tax_certificate(text):
    return "Steuerbescheinigung" in text and "Höhe der Kapitalerträge" in text


def parse_tax_certificate(text):
    """Liest die Kapitalertragsfelder zeilenweise; {} wenn kein solches Formular."""
    if not text or not is_tax_certificate(text):
        return {}

    lines = text.splitlines()
    fields = {}
    for index, line in enumerate(lines):
        for name, pattern in _LABELS:
            if name in fields or not pattern.search(line):
                continue

            # Zeilen ohne eigenen Betrag (z. B. "Zeile 48 Anlage KAP" oder die
            # Angabe der Religionsgemeinschaft) übergehen wir.
            amount = amount_near(lines, index)
            if amount is not None:
                fields[name] = abs(amount)
            break

    # Ohne den Kapitalertrag selbst haben wir das Formular nicht verstanden.
    if "interest" not in fields:
        return {}

    return fields

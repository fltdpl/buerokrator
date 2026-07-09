"""Jahreskontoauszüge: Salden, Zinsen und Beitragssumme per Bilanzregel.

Warum überhaupt eine Regel? Ein 4B-Modell kann die zwölf monatlichen
Sparbeiträge eines Jahresauszugs nicht aufsummieren — und muss es auch
nicht: die Beitragssumme folgt aus der Bilanz

    Beiträge = Endsaldo - Saldovortrag - Zinsen + Steuern

Das ist Buchhaltung und gilt für jeden Anbieter. Der Vorteil gegenüber
einer Summe: sie stimmt auch dann, wenn OCR einzelne Buchungszeilen
verschluckt hat (kommt vor, siehe Ground Truth).

Anbieterabhängig ist nur die *Erkennung* des Formulars. Sie steckt in
LAYOUTS; ein neuer Anbieter bekommt dort einen Eintrag und sonst nichts.
Passt kein Layout oder wirkt die Tabelle unvollständig, liefert der Parser
{} und die LLM-Extraktion bleibt unangetastet — bei fremden Dokumenten ist
Schweigen die richtige Antwort.

Bewusst NICHT gelesen: Aussteller, Produktname, Dokumentdatum. Die sind je
Anbieter verschieden und dürfen nicht aus einem Layout geraten werden.
"""

import re

from src.extraction.text_utils import signed_amounts

# Buchungszeilen am Tabellenende, in Dokumentreihenfolge. Vom Endsaldo aus
# zählen wir rückwärts, denn nur das Tabellenende ist stabil: bei
# spaltenweise ge-OCR-ten Auszügen fehlen mitunter Zeilen in der Mitte.
_TAIL_LABELS = (
    ("interest", re.compile(r"(Guthaben|Haben)zinsen", re.IGNORECASE)),
    ("capital_gains_tax", re.compile(r"Kapitalertrags?steuer", re.IGNORECASE)),
    ("soli", re.compile(r"Solidaritätszuschlag", re.IGNORECASE)),
)

_OPENING_LABEL = re.compile(r"Saldovortrag|Alter Saldo|Anfangssaldo", re.IGNORECASE)
_CLOSING_LABEL = re.compile(r"Endsaldo|Neuer Saldo|Schlusssaldo", re.IGNORECASE)

# Erkennung je Anbieter/Formular. `header` identifiziert das Dokument,
# `subtype` ist unser kanonischer Subtyp, `policy_label` die Beschriftung der
# Vertragsnummer (gelesen, nicht geraten).
LAYOUTS = (
    {
        "name": "bausparkasse_jahreskontoauszug",
        "header": re.compile(
            r"(Jahres)?[Kk]ontoauszug\s+\d{4}\s*-\s*Bausparkonto", re.IGNORECASE
        ),
        "subtype": "bauspar_jahresauszug",
        "policy_label": re.compile(r"Bausparnummer:?\s*(\d{6,})"),
    },
)

# Unter so vielen Beträgen ist die Tabelle nicht plausibel gelesen
# (Saldovortrag, mindestens eine Buchung, Zinsen, Steuer, Endsaldo).
_MIN_TABLE_AMOUNTS = 5


def match_layout(text):
    """Das erste passende Layout — oder None."""
    for layout in LAYOUTS:
        if layout["header"].search(text):
            return layout
    return None


def parse_account_statement(text):
    """Liest Salden, Zinsen und die abgeleitete Beitragssumme.

    Gibt {} zurück, wenn kein Layout greift oder die Betragsspalte nicht
    plausibel gelesen wurde.
    """
    if not text:
        return {}

    layout = match_layout(text)
    if layout is None:
        return {}

    if not (_OPENING_LABEL.search(text) and _CLOSING_LABEL.search(text)):
        return {}

    amounts = signed_amounts(text)
    if len(amounts) < _MIN_TABLE_AMOUNTS:
        return {}

    present = [name for name, pattern in _TAIL_LABELS if pattern.search(text)]
    if "interest" not in present:
        return {}

    opening_balance = amounts[0]
    closing_balance = amounts[-1]

    # Rückwärts vom Endsaldo: ..., Zinsen, [Steuer], [Soli], Endsaldo.
    tail = {}
    for offset, name in enumerate(reversed(present), start=2):
        tail[name] = abs(amounts[-offset])

    interest = tail["interest"]
    taxes = tail.get("capital_gains_tax", 0.0) + tail.get("soli", 0.0)
    contributions_total = round(closing_balance - opening_balance - interest + taxes, 2)

    if closing_balance <= opening_balance or contributions_total < 0:
        return {}

    fields = {
        "document_subtype": layout["subtype"],
        "interest": interest,
        "contributions_total": contributions_total,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
    }

    policy_number = layout["policy_label"].search(text)
    if policy_number:
        fields["policy_number"] = policy_number.group(1)

    return fields

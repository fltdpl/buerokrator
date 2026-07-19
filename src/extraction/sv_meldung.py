"""Regelparser für die Meldebescheinigung zur Sozialversicherung (§ 25 DEÜV).

Der Ausdruck trägt beschriftete Felder: „Art der Meldung - <Grund>" und die
Zeitraum-Tabelle „Von bis Entgelt". Beides liest der Parser deterministisch
vom layouttreu rekonstruierten Text (src/ocr/pdf_reader) — das LLM verwechselt
auf dem Formular regelmäßig Zeiträume und Meldegründe.

Wie überall: nur beschriftete Werte lesen, nichts Identifizierendes setzen
(Aussteller bleibt Sache des LLM), bei unbekanntem Layout {}.
"""

import re


def _compact(text):
    return re.sub(r"\s+", "", text.lower())


# Erkennungsanker: Titel + das beschriftete Meldegrund-Feld. („DEÜV" ist je
# nach Font-Encoding unleserlich — „DEèV" — und darum kein Anker.)
def is_sv_meldung(text):
    compact = _compact(text)

    return "sozialversicherung" in compact and "artdermeldung" in compact


# Kanonische Meldegründe (Suchwort auf dem kompakten Meldegrund-Rest).
# Stornierung zuerst: „Stornierung einer Jahresmeldung" soll als
# Stornierung erscheinen, nicht als Jahresmeldung.
_MELDEGRUENDE = (
    ("stornierung", "Stornierung"),
    ("jahresmeldung", "Jahresmeldung"),
    ("abmeldung", "Abmeldung"),
    ("anmeldung", "Anmeldung"),
    ("unterbrechung", "Unterbrechung"),
    ("sondermeldung", "Sondermeldung"),
)

# Zeitraum-Zeile der Tabelle „Von bis Entgelt": zwei Datumsangaben, auf der
# kompakten Zeile direkt aneinander („01.10.201831.12.2018002814euro…").
_PERIOD_PAIR = re.compile(
    r"(\d{2})\.(\d{2})\.(\d{4})(\d{2})\.(\d{2})\.(\d{4})"
)


def parse_sv_meldung(text):
    """Meldegrund + Meldezeitraum; bei unbekanntem Layout {}.

    Ein PDF kann MEHRERE Meldungen enthalten (Stornierung der alten plus
    korrigierte Neuausstellung). Dann zählt die letzte Nicht-Stornierung —
    sie ist der finale Stand; nur ein reiner Storno bleibt „Stornierung".
    """
    if not is_sv_meldung(text):
        return {}

    fields = {"document_subtype": "sv_meldung"}

    compact_lines = [_compact(line) for line in text.splitlines()]

    # Alle Meldegrund-Zeilen einsammeln: (Zeilenindex, Grund).
    meldungen = []

    for index, compact in enumerate(compact_lines):
        if "artdermeldung" not in compact:
            continue

        tail = compact.split("artdermeldung", 1)[1]

        for keyword, label in _MELDEGRUENDE:
            if keyword in tail:
                meldungen.append((index, label))
                break

    chosen_index = 0

    if meldungen:
        final = [entry for entry in meldungen if entry[1] != "Stornierung"]
        chosen_index, subject = final[-1] if final else meldungen[0]
        fields["subject"] = subject

    # Zeitraum aus der Entgelt-Tabellenzeile der GEWÄHLTEN Meldung (erste
    # Fundstelle ab deren Zeile; Fallback: erste im Dokument). Die
    # Euro-Bedingung verhindert, dass beliebige Datumspaare durchgehen.
    for offset in (chosen_index, 0):
        for compact in compact_lines[offset:]:
            if "euro" not in compact:
                continue

            pair = _PERIOD_PAIR.search(compact)

            if pair:
                d1, m1, y1, d2, m2, y2 = pair.groups()
                fields["period_start"] = f"{d1}.{m1}.{y1}"
                fields["period_end"] = f"{d2}.{m2}.{y2}"
                return fields

    return fields

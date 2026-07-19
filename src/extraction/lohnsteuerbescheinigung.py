"""Regelparser für den Ausdruck der elektronischen Lohnsteuerbescheinigung.

Das Formular trägt nummerierte, beschriftete Zeilen (3. Bruttoarbeitslohn,
22./23. Rentenversicherung, 25.–28. Sozialversicherung) — genau die Felder
der ELSTER-Anlagen N und Vorsorgeaufwand. Das LLM scheitert an dem
zweispaltigen Layout regelmäßig; der Parser liest deterministisch.

Arbeitet auf dem layouttreu rekonstruierten Text (src/ocr/pdf_reader):
Label und Betrag stehen dort auf einer visuellen Zeile, Spaltensprünge sind
als Doppel-Leerzeichen markiert. Der Parser ist whitespace-tolerant, weil
schmale Glyphen Wörter und Beträge trotzdem zerreißen können
(„Bruttoarbeitsloh n", „8 69 14"): Labels werden auf der leerzeichenfreien
Zeile gesucht, im Wertesegment zählen nur die Ziffern, die letzten zwei
sind die Cents.

Regeln des Projekts: nur beschriftete Werte lesen, nichts Identifizierendes
konstant setzen (Arbeitgeber bleibt Sache des LLM), bei unbekanntem Layout
leeres Ergebnis.
"""

import re

# Erkennungsanker: Titel des amtlichen Ausdrucks (Encoding-tolerant, „für"
# erscheint je nach Font-Encoding auch als „fÞr" o. Ä.).
_TITLE = re.compile(r"lohnsteuerbescheinigungf.{0,2}r(\d{4})")

# Zeilen-Labels als Muster auf der KOMPAKTEN Zeile (kleingeschrieben, ohne
# Leerraum). Die Zeilennummer gehört zum Muster, damit „4. Einbehaltene
# Lohnsteuer" nicht mit „11. Einbehaltene Lohnsteuer" (ermäßigt besteuerte
# Bezüge) verwechselt wird; (?<!\d) schützt vor Treffern in 14./24. usw.
_LINE_LABELS = (
    ("gross_amount", r"(?<!\d)3\.bruttoarbeitslohn"),
    ("income_tax", r"(?<!\d)4\.einbehaltenelohnsteuer"),
    ("soli", r"(?<!\d)5\.einbehaltenersol"),
    ("church_tax", r"(?<!\d)6\.einbehaltenekirchensteuer"),
    ("pension_insurance_employer", r"(?<!\d)22\.arbeitgeber"),
    ("pension_insurance_employee", r"(?<!\d)23\.arbeitnehmer"),
    ("health_insurance", r"(?<!\d)25\.arbeitnehmerbeitr"),
    ("care_insurance", r"(?<!\d)26\.arbeitnehmerbeitr"),
    ("unemployment_insurance", r"(?<!\d)27\.arbeitnehmerbeitr"),
    ("private_health_insurance", r"(?<!\d)28\.beitr"),
)

_COMPILED_LABELS = tuple(
    (field, re.compile(pattern)) for field, pattern in _LINE_LABELS
)

# Der Sozialversicherungs-Block (Zeilen 22–28): ein LEERES Wertefeld
# bedeutet auf dem amtlichen Ausdruck „kein Beitrag bescheinigt" → 0.0.
# Für die Steuerzeilen 3–6 gilt das bewusst NICHT (dort wäre eine stille
# 0 bei einem Parserfehler gefährlicher als ein fehlender Wert).
_BLANK_IS_ZERO = {
    "pension_insurance_employer",
    "pension_insurance_employee",
    "health_insurance",
    "care_insurance",
    "unemployment_insurance",
    "private_health_insurance",
}

# Bescheinigungszeitraum auf der kompakten Zeile: „01.01.-30.09." — die
# Punkte können bei der Rekonstruktion verloren gehen („0101-3009").
_PERIOD = re.compile(r"(\d{2})\.?(\d{2})\.?-+(\d{2})\.?(\d{2})")

# Ein Wertesegment (letzte Spalte einer Zeile): nur Ziffern, Punkte,
# Kommas und Leerraum.
_VALUE_SEGMENT = re.compile(r"^[\d\s.,]+$")

# Leermarkierung des Formulars („- - - - -"): der Wert ist bescheinigt 0.
_EMPTY_MARKER = re.compile(r"^[-\s/]+$")


def _compact(line):
    return re.sub(r"\s+", "", line.lower())


def is_lohnsteuerbescheinigung(text):
    return _TITLE.search(_compact(text)) is not None


def _segment_value(segment):
    """Betrag aus einem Wertesegment: Ziffern sammeln, letzte zwei = Cent."""
    if _EMPTY_MARKER.match(segment):
        return 0.0

    if not _VALUE_SEGMENT.match(segment.strip()):
        return None

    digits = re.sub(r"\D", "", segment)

    if len(digits) < 3:
        # Ein-/zweistellige Ziffernreste (z. B. Zeilennummern) sind kein
        # Euro-Cent-Betrag.
        return None

    return float(f"{digits[:-2]}.{digits[-2:]}")


def _line_value(line):
    """Wert der letzten Spalte einer Label-Zeile (None, wenn keiner da).

    Die Wertespalte kann durch die Glyph-Lücken selbst in mehrere Segmente
    zerfallen („1 .  053 70" = 1.053,70) — deshalb werden numerische
    Segmente vom Zeilenende her zusammengeführt, bis ein nicht-numerisches
    Segment (der Labeltext) die Wertespalte begrenzt.
    """
    segments = re.split(r"\s{2,}", line.strip())

    if len(segments) < 2:
        return None

    numeric_tail = []

    for segment in reversed(segments[1:]):
        if _VALUE_SEGMENT.match(segment.strip()) or _EMPTY_MARKER.match(segment):
            numeric_tail.append(segment)

        else:
            break

    if not numeric_tail:
        return None

    return _segment_value(" ".join(reversed(numeric_tail)))


def _pure_value_line(line):
    """Betrag einer reinen Wertezeile (Zeile besteht NUR aus dem Wert)."""
    stripped = line.strip()

    if not stripped or not _VALUE_SEGMENT.match(stripped):
        return None

    return _segment_value(stripped)


def parse_lohnsteuerbescheinigung(text):
    """Felder der Anlagen N/Vorsorgeaufwand aus dem amtlichen Ausdruck.

    Liefert nur sicher zuordenbare Felder; bei unbekanntem Layout {}.
    """
    lines = text.splitlines()
    compact_lines = [_compact(line) for line in lines]

    title = _TITLE.search(_compact(text))

    if title is None:
        return {}

    year = title.group(1)
    fields = {"document_subtype": "lohnsteuerbescheinigung", "tax_year": year}

    for compact in compact_lines:
        if "zeitraum" in compact and "lohnzahlung" not in compact:
            # Nur hinter dem Label suchen, damit keine fremden Ziffern
            # (Anschrift, Steuernummer) als Datum durchgehen.
            period = _PERIOD.search(compact.split("zeitraum", 1)[1])

            if period:
                d1, m1, d2, m2 = period.groups()
                fields["period_start"] = f"{d1}.{m1}.{year}"
                fields["period_end"] = f"{d2}.{m2}.{year}"
                break

    used_value_lines = set()

    for field, pattern in _COMPILED_LABELS:
        for index, compact in enumerate(compact_lines):
            if not pattern.search(compact):
                continue

            value = _value_for_line(lines, index, used_value_lines)

            if value is None and field in _BLANK_IS_ZERO:
                value = 0.0

            if value is not None:
                fields[field] = value

            break

    _apply_pension_fallback(fields, lines, compact_lines, used_value_lines)
    _apply_private_health_fallback(fields, lines, compact_lines, used_value_lines)

    return fields


def _value_for_line(lines, index, used_value_lines):
    """Wert einer Label-Zeile: erst die Zeile selbst, dann die Nachbarn.

    Wert-Zeilen liegen im Formular teils vertikal ZWISCHEN zwei
    Label-Zeilen (halbzeilig versetzt) — deshalb auch die Zeilen darüber
    und darunter prüfen. Jede Zeile gibt ihren Wert nur einmal her.
    """
    value = _line_value(lines[index])

    if value is not None:
        return value

    for neighbor in (index + 1, index + 2, index - 1, index - 2):
        if not 0 <= neighbor < len(lines) or neighbor in used_value_lines:
            continue

        value = _pure_value_line(lines[neighbor])

        if value is None:
            value = _line_value(lines[neighbor])

        if value is not None:
            used_value_lines.add(neighbor)
            return value

    return None


def _apply_pension_fallback(fields, lines, compact_lines, used_value_lines):
    """Zeilen 22/23 über die „Rentenversicherung"-Wertzeilen.

    Die zweizeiligen Mikroschrift-Labels („22. Arbeitgeber- / anteil")
    überleben die Rekonstruktion oft nicht — die Beschriftung
    „a) zur gesetzlichen Rentenversicherung" der Wertspalte schon. Im
    LStB-Ausdruck tragen genau zwei solcher Zeilen Werte: erst der
    Arbeitgeber- (22), dann der Arbeitnehmeranteil (23).
    """
    if (
        "pension_insurance_employer" in fields
        and "pension_insurance_employee" in fields
    ):
        return

    values = []

    for index, compact in enumerate(compact_lines):
        if "rentenversicherung" not in compact:
            continue

        value = _value_for_line(lines, index, used_value_lines)

        if value is not None:
            values.append(value)

    if not values:
        return

    fields.setdefault("pension_insurance_employer", values[0])
    # Nur eine Wertzeile gefunden: die Beiträge sind paritätisch — der
    # zweite Wert ist auf dem Formular identisch bescheinigt.
    fields.setdefault(
        "pension_insurance_employee", values[1] if len(values) > 1 else values[0]
    )


def _apply_private_health_fallback(fields, lines, compact_lines, used_value_lines):
    """Zeile 28 über ihre (robuste) Fortsetzungszeile.

    Das Label „28. Beiträge zur privaten Kranken- u. Pflege-" zerfällt in
    Mikroschrift; die Fortsetzung „Pflichtversicherung oder
    Mindestvorsorgepauschale" ist eindeutig und übersteht die
    Rekonstruktion.
    """
    if "private_health_insurance" in fields:
        return

    for index, compact in enumerate(compact_lines):
        if "mindestvorsorgepauschale" not in compact:
            continue

        value = _value_for_line(lines, index, used_value_lines)
        # Leeres Feld = kein Beitrag bescheinigt (wie im SV-Block üblich).
        fields["private_health_insurance"] = value if value is not None else 0.0
        return

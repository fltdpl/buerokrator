"""Reine Vergleichslogik: erwartete vs. tatsächliche Pipeline-Ergebnisse.

Bewusst ohne LLM-/OCR-Abhängigkeiten, damit sie vollständig testbar ist.
"""

import re
from datetime import date

# Toleranz für Betragsvergleiche (Rundungsdifferenzen der Normalisierung).
AMOUNT_TOLERANCE = 0.01

# Kurzer Text (z. B. "AG") darf nicht per Teilstring matchen.
MIN_CONTAINMENT_LENGTH = 4

GERMAN_MONTHS = {
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

_DATE_PATTERNS = (
    # 31.12.2022 / 1.2.2022
    (re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$"), ("d", "m", "y")),
    # 2022-12-31
    (re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"), ("y", "m", "d")),
)


def _parse_date(value):
    """Parst gängige Datumsschreibweisen ("31.12.2022", "2022-12-31",
    "5. Mai 2026") zu einem date — sonst None."""
    if not isinstance(value, str):
        return None

    text = value.strip()

    for pattern, order in _DATE_PATTERNS:
        match = pattern.match(text)
        if match:
            parts = dict(zip(order, match.groups()))
            try:
                return date(int(parts["y"]), int(parts["m"]), int(parts["d"]))
            except ValueError:
                return None

    # "5. Mai 2026"
    match = re.match(r"^(\d{1,2})\.?\s+([A-Za-zäöüÄÖÜ]+)\s+(\d{4})$", text)
    if match:
        month = GERMAN_MONTHS.get(match.group(2).lower())
        if month:
            try:
                return date(int(match.group(3)), month, int(match.group(1)))
            except ValueError:
                return None

    return None


# Häufige Firmierungs-Varianten, die dieselbe Firma bezeichnen.
_COMPANY_FORM_ALIASES = (
    ("aktiengesellschaft", "ag"),
    ("gesellschaft mit beschränkter haftung", "gmbh"),
)


def _normalize_string(value):
    text = " ".join(str(value).strip().casefold().split())

    for long_form, short_form in _COMPANY_FORM_ALIASES:
        text = text.replace(long_form, short_form)

    return text


def _is_empty(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _as_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def values_match(expected, actual):
    """Vergleicht einen erwarteten mit einem extrahierten Feldwert.

    - leer erwartet (None/"") matcht leer extrahiert
    - Daten in verschiedenen Schreibweisen werden als Datum verglichen
    - Zahlen (auch als String) numerisch mit Toleranz
    - sonst normalisierter Stringvergleich; zusätzlich gilt Enthaltensein
      als Treffer ("Debeka Bausparkasse" vs. "Debeka Bausparkasse AG"),
      damit Aussteller-Varianten die Messung nicht verrauschen
    """
    if _is_empty(expected):
        return _is_empty(actual)

    expected_date = _parse_date(expected)
    if expected_date is not None:
        actual_date = _parse_date(actual) if not _is_empty(actual) else None
        return actual_date == expected_date

    expected_number = _as_number(expected)
    if expected_number is not None:
        actual_number = _as_number(actual)
        if actual_number is None:
            return False
        return abs(expected_number - actual_number) <= AMOUNT_TOLERANCE

    if _is_empty(actual):
        return False

    expected_text = _normalize_string(expected)
    actual_text = _normalize_string(actual)

    if expected_text == actual_text:
        return True

    if (
        min(len(expected_text), len(actual_text)) >= MIN_CONTAINMENT_LENGTH
        and (expected_text in actual_text or actual_text in expected_text)
    ):
        return True

    return False


def compare_document(case, actual_type, actual_fields):
    """Vergleicht ein Dokument gegen seine Ground Truth.

    Liefert pro Feld einen Status:
      correct — Wert stimmt (innerhalb Toleranz)
      wrong   — Feld extrahiert, aber falscher Wert
      missing — erwartetes Feld fehlt in der Extraktion
    Zusätzlich 'spurious': extrahierte Felder ohne Ground-Truth-Erwartung
    (nicht als Fehler gewertet, aber ausgewiesen).
    """
    actual_fields = actual_fields or {}
    expected_fields = case["fields"]

    field_results = {}
    for field, expected in expected_fields.items():
        if field not in actual_fields:
            # Erwartet "kein Wert" (None/"") + Feld nicht extrahiert = korrekt.
            status = "correct" if _is_empty(expected) else "missing"
            field_results[field] = {"status": status, "expected": expected, "actual": None}
        elif values_match(expected, actual_fields[field]):
            field_results[field] = {
                "status": "correct",
                "expected": expected,
                "actual": actual_fields[field],
            }
        else:
            field_results[field] = {
                "status": "wrong",
                "expected": expected,
                "actual": actual_fields[field],
            }

    spurious = sorted(set(actual_fields) - set(expected_fields))
    correct = sum(1 for r in field_results.values() if r["status"] == "correct")

    return {
        "name": case["name"],
        "file": case["file"],
        "verified": case["verified"],
        "expected_type": case["document_type"],
        "actual_type": actual_type,
        "type_correct": actual_type == case["document_type"],
        "fields": field_results,
        "spurious": spurious,
        "fields_total": len(expected_fields),
        "fields_correct": correct,
    }


def aggregate_results(results):
    """Aggregiert Dokumentergebnisse zu Gesamt- und Pro-Typ-Metriken."""
    total_docs = len(results)
    type_correct = sum(1 for r in results if r["type_correct"])
    fields_total = sum(r["fields_total"] for r in results)
    fields_correct = sum(r["fields_correct"] for r in results)

    by_type = {}
    for r in results:
        stats = by_type.setdefault(
            r["expected_type"],
            {"docs": 0, "type_correct": 0, "fields_total": 0, "fields_correct": 0},
        )
        stats["docs"] += 1
        stats["type_correct"] += 1 if r["type_correct"] else 0
        stats["fields_total"] += r["fields_total"]
        stats["fields_correct"] += r["fields_correct"]

    # Klassifikationsquelle (Regel vs. LLM): zeigt, welcher Pfad Fehler macht.
    by_source = {}
    for r in results:
        source = r.get("classification_source", "llm")
        stats = by_source.setdefault(source, {"docs": 0, "type_correct": 0})
        stats["docs"] += 1
        stats["type_correct"] += 1 if r["type_correct"] else 0

    return {
        "documents": total_docs,
        "unverified": sum(1 for r in results if not r["verified"]),
        "classification_accuracy": type_correct / total_docs if total_docs else None,
        "field_accuracy": fields_correct / fields_total if fields_total else None,
        "fields_total": fields_total,
        "fields_correct": fields_correct,
        "by_type": by_type,
        "by_source": by_source,
    }

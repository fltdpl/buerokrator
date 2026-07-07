"""Reine Vergleichslogik: erwartete vs. tatsächliche Pipeline-Ergebnisse.

Bewusst ohne LLM-/OCR-Abhängigkeiten, damit sie vollständig testbar ist.
"""

# Toleranz für Betragsvergleiche (Rundungsdifferenzen der Normalisierung).
AMOUNT_TOLERANCE = 0.01


def _normalize_string(value):
    return " ".join(str(value).strip().casefold().split())


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

    Zahlen (auch als String) werden numerisch mit Toleranz verglichen,
    alles andere als normalisierter String (Groß-/Kleinschreibung,
    Whitespace egal).
    """
    if expected is None:
        return actual is None

    expected_number = _as_number(expected)
    if expected_number is not None:
        actual_number = _as_number(actual)
        if actual_number is None:
            return False
        return abs(expected_number - actual_number) <= AMOUNT_TOLERANCE

    if actual is None:
        return False

    return _normalize_string(expected) == _normalize_string(actual)


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
            # Erwartet "kein Wert" + Feld nicht extrahiert = korrekt.
            status = "correct" if expected is None else "missing"
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

    return {
        "documents": total_docs,
        "unverified": sum(1 for r in results if not r["verified"]),
        "classification_accuracy": type_correct / total_docs if total_docs else None,
        "field_accuracy": fields_correct / fields_total if fields_total else None,
        "fields_total": fields_total,
        "fields_correct": fields_correct,
        "by_type": by_type,
    }

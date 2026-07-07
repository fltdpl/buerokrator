import json
from pathlib import Path

from src.classifier.document_classifier import classify
from src.classifier.document_extractor import extract_document
from src.evaluation.comparator import aggregate_results, compare_document
from src.evaluation.ground_truth import load_ground_truth


def evaluate_case(case):
    """Führt Klassifikation + Extraktion für einen Ground-Truth-Fall aus."""
    text = case["document_text"]
    classification = classify(text)
    actual_type = classification["document_type"]

    # Extraktion mit dem ERKANNTEN Typ: gemessen wird die echte Pipeline,
    # nicht die Extraktion unter Idealbedingungen.
    actual_fields = extract_document(actual_type, text) or {}

    return compare_document(case, actual_type, actual_fields)


def run_evaluation(document_type=None, limit=None):
    cases = load_ground_truth(document_type=document_type, limit=limit)

    if not cases:
        raise SystemExit(
            "Keine geprüften Dokumente mit Text in der Datenbank gefunden "
            "(verified = 1 und document_text gesetzt)."
        )

    results = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['name']}")
        results.append(evaluate_case(case))

    return {"summary": aggregate_results(results), "results": results}


def format_report(report):
    """Formatiert den Evaluationsbericht als lesbaren Text."""
    summary = report["summary"]
    lines = ["", "=== Extraktionsqualität ===", ""]

    def percent(value):
        return f"{value * 100:.0f} %" if value is not None else "—"

    lines.append(f"Dokumente:            {summary['documents']}")
    lines.append(f"Klassifikation:       {percent(summary['classification_accuracy'])}")
    lines.append(
        f"Felder korrekt:       {summary['fields_correct']}/{summary['fields_total']}"
        f" ({percent(summary['field_accuracy'])})"
    )

    lines.append("")
    lines.append("Pro Typ:")
    for doc_type, stats in sorted(summary["by_type"].items()):
        field_part = (
            f"Felder {stats['fields_correct']}/{stats['fields_total']}"
            if stats["fields_total"]
            else "keine Felder"
        )
        lines.append(
            f"  {doc_type:<10} Typ {stats['type_correct']}/{stats['docs']}, {field_part}"
        )

    problems = [
        r
        for r in report["results"]
        if not r["type_correct"] or r["fields_correct"] < r["fields_total"]
    ]
    if problems:
        lines.append("")
        lines.append(f"Abweichungen ({len(problems)} Dokumente):")
        for r in problems:
            lines.append(f"  {r['name']}:")
            if not r["type_correct"]:
                lines.append(
                    f"    Typ: erwartet {r['expected_type']}, erkannt {r['actual_type']}"
                )
            for field, detail in r["fields"].items():
                if detail["status"] == "missing":
                    lines.append(f"    {field}: FEHLT (erwartet: {detail['expected']})")
                elif detail["status"] == "wrong":
                    lines.append(
                        f"    {field}: erwartet {detail['expected']!r},"
                        f" extrahiert {detail['actual']!r}"
                    )

    lines.append("")
    return "\n".join(lines)


def save_report(report, path="exports/evaluation_report.json"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path

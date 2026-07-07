"""Misst Klassifikations- und Extraktionsqualität gegen die Datenbank.

Ground Truth sind alle in der App geprüften Dokumente (verified = 1):
ihre korrigierten Felder gelten als Sollwerte, der gespeicherte OCR-Text
als Eingabe. Für jedes Dokument läuft Klassifikation + Extraktion neu und
wird mit den Sollwerten verglichen.

  python evaluate.py                  # alle geprüften Dokumente
  python evaluate.py --type pension   # nur ein Dokumenttyp
  python evaluate.py --limit 20       # Stichprobe für schnelle Läufe

Textreport auf stdout, JSON-Report in exports/evaluation_report.json.
"""

import argparse

from src.evaluation.runner import format_report, run_evaluation, save_report


def main():
    parser = argparse.ArgumentParser(description="Extraktionsqualität messen")
    parser.add_argument("--type", help="nur diesen Dokumenttyp prüfen")
    parser.add_argument("--limit", type=int, help="maximale Anzahl Dokumente")
    args = parser.parse_args()

    report = run_evaluation(document_type=args.type, limit=args.limit)
    print(format_report(report))
    path = save_report(report)
    print(f"JSON-Report: {path}")


if __name__ == "__main__":
    main()

"""Golden-Master-Abgleich: ELSTER-Zuordnung gegen die abgegebene Erklärung.

Vertrauens-Workflow (docs/04_Steuerlogik.md): die Erwartungswerte stammen
aus der tatsächlich abgegebenen Steuererklärung (Ausdruck des
Steuerprogramms oder Bescheid) und
liegen als tax_expected_<jahr>.yaml neben diesem Skript (gitignored — echte
Steuerdaten).

  python -m tools.tax_check 2025             # Abgleich
  python -m tools.tax_check 2025 --vorlage   # leere Erwartungs-Vorlage

Der Abgleich ist ein Hilfsmittel, um kritische Stellen zu finden — kein
hartes Abnahme-Kriterium; erklärte Differenzen lassen sich in der
Erwartungsdatei mit `position: ignoriert` ausklammern.
Exit-Code 0 = alle geprüften Positionen stimmen, sonst 1.
"""

import argparse
import sys
from pathlib import Path

import yaml

from src.tax.elster_check import build_template, compare_year, format_report


def expectation_path(year):
    """Neben dem Skript, nicht cwd-relativ — sonst hinge die Datei daran,
    aus welchem Verzeichnis der Abgleich gestartet wurde."""
    return Path(__file__).resolve().parent / f"tax_expected_{year}.yaml"


def write_template(year):
    path = expectation_path(year)

    if path.exists():
        print(f"{path} existiert bereits — nicht überschrieben.")
        return 1

    path.write_text(build_template(year), encoding="utf-8")
    print(f"Vorlage angelegt: {path}")
    print("Werte aus der abgegebenen Erklärung eintragen, dann:")
    print(f"  python -m tools.tax_check {year}")
    return 0


def run_check(year):
    path = expectation_path(year)

    if not path.exists():
        print(f"Erwartungsdatei {path} fehlt.")
        print(f"Vorlage anlegen mit: python -m tools.tax_check {year} --vorlage")
        return 1

    expected = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    report = compare_year(year, expected)
    print(format_report(report))

    return 0 if report["ok"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="ELSTER-Werte gegen die abgegebene Erklärung abgleichen"
    )
    parser.add_argument("jahr", type=int, help="Steuerjahr, z. B. 2025")
    parser.add_argument(
        "--vorlage",
        action="store_true",
        help="leere Erwartungs-Vorlage anlegen statt abzugleichen",
    )
    args = parser.parse_args()

    if args.vorlage:
        sys.exit(write_template(args.jahr))

    sys.exit(run_check(args.jahr))


if __name__ == "__main__":
    main()

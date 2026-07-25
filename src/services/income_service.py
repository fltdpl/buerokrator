"""Jahreseinkommen aus geprüften Lohnsteuerbescheinigungen (framework-frei).

Datengrundlage der Einkommens-Auswertung auf der Analyse-Seite: je Jahr
Brutto, Steuern (Lohnsteuer + Soli + Kirchensteuer) und ein RECHNERISCHES
Netto (Brutto − Steuern − Arbeitnehmer-Anteile der Sozialversicherung,
LStB Zeilen 23/25/26/27). Das echte Auszahlungs-Netto kennt nur die
Gehaltsabrechnung — VWL, bAV o. Ä. fehlen hier bewusst; die Beiträge zur
privaten Kranken-/Pflegeversicherung (Zeile 28) zahlt der Nutzer direkt,
sie sind kein Lohnabzug und bleiben deshalb außen vor.

Es zählen nur geprüfte UND steuerrelevante Bescheinigungen (dieselbe Regel
wie in der Anlage N); mehrere Bescheinigungen desselben Jahres — etwa bei
Teilzeit oder Arbeitgeberwechsel — addieren sich. Jahre ohne Bescheinigung
fehlen in der Rückgabe (Lücke, keine stille 0).
"""

import json

from src.core.amount_utils import normalize_amount
from src.database.list_documents import list_documents
from src.organizer.date_utils import year_from_archive_path
from src.tax.tax_relevance import resolve_tax_relevance

TAX_FIELDS = ("income_tax", "soli", "church_tax")

# Arbeitnehmer-Anteile der Sozialversicherung (LStB Zeilen 23/25/26/27).
EMPLOYEE_SOCIAL_FIELDS = (
    "pension_insurance_employee",
    "health_insurance",
    "care_insurance",
    "unemployment_insurance",
)


def _parse_data(raw):
    if not raw:
        return {}

    try:
        data = json.loads(raw)

    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _document_year(row, data):
    """Steuerjahr: tax_year-Feld, sonst Archivjahr (wie elster_mapping)."""
    tax_year = data.get("tax_year")

    if tax_year is not None:
        try:
            return int(str(tax_year).strip())

        except (TypeError, ValueError):
            pass

    return year_from_archive_path(row["archive_path"])


def _reference(row, data):
    return {
        "id": row["id"],
        "filename": row["filename"],
        "employer": data.get("employer") or "",
    }


def _sum_fields(data, fields):
    return sum(normalize_amount(data.get(field)) or 0.0 for field in fields)


def build_income_series(documents: list[dict] | None = None) -> list[dict]:
    """Jahresreihe: je Jahr Brutto/Steuern/rechnerisches Netto + Belege.

    Rückgabe aufsteigend nach Jahr, nur Jahre mit mindestens einer
    Lohnsteuerbescheinigung. Je Eintrag:
    - brutto/steuern/netto: Summen der geprüften Bescheinigungen
    - documents: gezählte Belege (Referenzen mit id/filename/employer)
    - pending: ungeprüfte Bescheinigungen (zählen NICHT)
    - missing_value: geprüfte ohne Bruttoarbeitslohn (zählen NICHT)
    """
    if documents is None:
        documents = list_documents()

    years: dict[int, dict] = {}

    for row in documents:
        data = _parse_data(row["extracted_data"])

        if row["document_type"] != "employment":
            continue

        if data.get("document_subtype") != "lohnsteuerbescheinigung":
            continue

        # Dieselbe Regel wie in der Anlage N: explizit als „nicht
        # steuerrelevant" markierte Bescheinigungen (z. B. Duplikate)
        # zählen nicht.
        if not resolve_tax_relevance(
            row["document_type"], data, row["tax_relevant"]
        ):
            continue

        year = _document_year(row, data)

        if year is None:
            continue

        entry = years.setdefault(
            year,
            {
                "year": year,
                "brutto": 0.0,
                "steuern": 0.0,
                "netto": 0.0,
                "documents": [],
                "pending": [],
                "missing_value": [],
            },
        )

        if not row["verified"]:
            entry["pending"].append(_reference(row, data))
            continue

        brutto = normalize_amount(data.get("gross_amount"))

        if brutto is None:
            # Ohne Bruttoarbeitslohn wäre jedes Netto Unsinn — der Beleg
            # wird ausgewiesen statt still mitgezählt.
            entry["missing_value"].append(_reference(row, data))
            continue

        steuern = _sum_fields(data, TAX_FIELDS)
        sozialabgaben = _sum_fields(data, EMPLOYEE_SOCIAL_FIELDS)

        entry["brutto"] += brutto
        entry["steuern"] += steuern
        entry["netto"] += brutto - steuern - sozialabgaben
        entry["documents"].append(_reference(row, data))

    return [years[year] for year in sorted(years)]

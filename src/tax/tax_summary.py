import csv
import json
from io import StringIO

from src.core.amount_utils import normalize_amount
from src.core.document_types import (
    BANK,
    HOUSING,
    INSURANCE,
    INVOICE,
    PENSION,
    TAX,
    UNKNOWN,
)
from src.database.list_documents import list_documents
from src.organizer.date_utils import year_from_archive_path

# Zuordnung Dokumenttyp -> Steuer-/Übersichtskategorie.
# Bewusst grobe erste Zuordnung (die Steuerlogik-Doku ist WIP), zentral und
# leicht verfeinerbar (z. B. später nach insurance_type differenzieren:
# Kranken-/Pflege als Sonderausgaben vs. sonstige Vorsorge).
TAX_CATEGORY_BY_TYPE = {
    INSURANCE: "vorsorgeaufwendungen",
    PENSION: "altersvorsorge",
    TAX: "einkommen",
    HOUSING: "wohnen",
    INVOICE: "rechnungen",
    BANK: "bank",
    UNKNOWN: "sonstiges",
}

TAX_CATEGORY_LABELS = {
    "vorsorgeaufwendungen": "Vorsorgeaufwendungen (Sonderausgaben)",
    "altersvorsorge": "Altersvorsorge & Vermögensaufbau",
    "einkommen": "Einkommen & Lohnsteuer",
    "wohnen": "Wohnen",
    "rechnungen": "Rechnungen",
    "bank": "Bank",
    "sonstiges": "Sonstiges",
}

# Anzeigereihenfolge: steuerlich relevante Kategorien zuerst.
TAX_CATEGORY_ORDER = [
    "vorsorgeaufwendungen",
    "altersvorsorge",
    "einkommen",
    "wohnen",
    "rechnungen",
    "bank",
    "sonstiges",
]

# Kategorien, deren Beträge als steuerlich absetzbar aufsummiert werden.
DEDUCTIBLE_CATEGORIES = {"vorsorgeaufwendungen"}


def tax_category_for_type(document_type):
    return TAX_CATEGORY_BY_TYPE.get(document_type, "sonstiges")


def _parse_data(raw):
    if not raw:
        return {}

    try:
        data = json.loads(raw)

    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def available_tax_years(documents=None):
    if documents is None:
        documents = list_documents()

    years = {year_from_archive_path(row[2]) for row in documents}

    return sorted(year for year in years if year is not None)


def _new_category_entry(category):
    return {
        "category": category,
        "label": TAX_CATEGORY_LABELS.get(category, category),
        "deductible": category in DEDUCTIBLE_CATEGORIES,
        "count": 0,
        "verified_count": 0,
        "amount": 0.0,
        "verified_amount": 0.0,
        "documents": [],
    }


def build_tax_summary(year, documents=None):
    """Aggregiert alle Dokumente eines Archivjahres zu einer Steuerübersicht.

    Gruppiert nach Steuerkategorie, summiert Beträge und trennt geprüfte von
    ungeprüften Werten, damit ungeprüfte LLM-Zahlen eine Summe nicht still
    verfälschen.
    """
    if documents is None:
        documents = list_documents()

    categories = {}
    totals = {
        "count": 0,
        "amount": 0.0,
        "verified_amount": 0.0,
        "deductible_amount": 0.0,
        "deductible_verified_amount": 0.0,
    }

    for row in documents:
        if year_from_archive_path(row[2]) != year:
            continue

        document_type = row[3]
        category = tax_category_for_type(document_type)
        data = _parse_data(row[4])
        amount = normalize_amount(data.get("amount"))
        verified = bool(row[5])

        entry = categories.setdefault(category, _new_category_entry(category))

        entry["count"] += 1
        totals["count"] += 1

        if verified:
            entry["verified_count"] += 1

        if amount is not None:
            entry["amount"] += amount
            totals["amount"] += amount

            if verified:
                entry["verified_amount"] += amount
                totals["verified_amount"] += amount

            if entry["deductible"]:
                totals["deductible_amount"] += amount

                if verified:
                    totals["deductible_verified_amount"] += amount

        entry["documents"].append(
            {
                "id": row[0],
                "filename": row[1],
                "document_type": document_type,
                "amount": amount,
                "verified": verified,
                "document_date": data.get("document_date", ""),
                "issuer": (
                    data.get("issuer")
                    or data.get("insurer")
                    or data.get("employer")
                    or ""
                ),
            }
        )

    ordered = [categories[key] for key in TAX_CATEGORY_ORDER if key in categories]

    # Unerwartete Kategorien (z. B. nach Erweiterung der Dokumenttypen) hinten
    # anhängen, statt sie stillschweigend zu verlieren.
    for key, entry in categories.items():
        if key not in TAX_CATEGORY_ORDER:
            ordered.append(entry)

    return {
        "year": year,
        "categories": ordered,
        "totals": totals,
    }


def export_tax_summary_csv(summary):
    """Jahres-CSV je Dokument gemäß docs/05_Steuerlogik.md.

    Spalten: Datum, Kategorie, Betrag, Geprueft, Dokumentreferenz.
    """
    output = StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "Datum",
            "Kategorie",
            "Betrag",
            "Geprueft",
            "Dokumentreferenz",
        ]
    )

    for category in summary["categories"]:
        for document in category["documents"]:
            amount = document["amount"]

            writer.writerow(
                [
                    document["document_date"],
                    category["label"],
                    "" if amount is None else f"{amount:.2f}",
                    "ja" if document["verified"] else "nein",
                    document["filename"],
                ]
            )

    return output.getvalue()

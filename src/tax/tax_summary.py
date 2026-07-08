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

# Kategorien, die absetzbare Dokumente enthalten können (Label/Reihenfolge).
# Ob ein einzelnes Dokument zählt, entscheidet document_deductibility().
DEDUCTIBLE_CATEGORIES = {"vorsorgeaufwendungen"}

# Absetzbarkeit je Dokument (siehe docs/05_Steuerlogik.md, bewusst grob):
# Versicherungen werden nach insurance_type unterschieden — Vorsorge
# (Sonderausgaben/sonstige Vorsorgeaufwendungen) ist absetzbar, reine
# Sachversicherungen nicht. Unbekannte Arten landen in "unclear" und werden
# separat ausgewiesen statt still mitsummiert.
DEDUCTIBLE = "deductible"
NOT_DEDUCTIBLE = "not_deductible"
UNCLEAR = "unclear"

# Reihenfolge wichtig: Zusatzversicherungen wie "Lebensversicherung -
# Unfall-Zusatzversicherung" sollen über den Vorsorge-Anteil zählen.
DEDUCTIBLE_INSURANCE_KEYWORDS = (
    "kranken",
    "pflege",
    "haftpflicht",
    "unfall",
    "berufsunfähigkeit",
    "berufsunfaehigkeit",
    "risikoleben",
    "arbeitslosen",
)

# Kapital-Lebensversicherungen (Abschluss ab 2005) sind nicht absetzbar;
# Altverträge wären es anteilig — das bleibt bewusst außen vor.
NON_DEDUCTIBLE_INSURANCE_KEYWORDS = (
    "hausrat",
    "rechtsschutz",
    "gebäude",
    "gebaeude",
    "kasko",
    "reise",
    "lebensversicherung",
)


def document_deductibility(document_type, data):
    """Absetzbarkeit eines einzelnen Dokuments (deductible/not/unclear)."""
    if document_type != INSURANCE:
        category = tax_category_for_type(document_type)
        return DEDUCTIBLE if category in DEDUCTIBLE_CATEGORIES else NOT_DEDUCTIBLE

    insurance_type = data.get("insurance_type")
    if not isinstance(insurance_type, str) or not insurance_type.strip():
        return UNCLEAR

    lowered = insurance_type.lower()

    if any(keyword in lowered for keyword in DEDUCTIBLE_INSURANCE_KEYWORDS):
        return DEDUCTIBLE

    if any(keyword in lowered for keyword in NON_DEDUCTIBLE_INSURANCE_KEYWORDS):
        return NOT_DEDUCTIBLE

    return UNCLEAR

# tax-Dokumente haben kein generisches amount — ihre Beträge liegen in
# benannten Feldern. Pro Subtyp das aussagekräftigste Feld für die Übersicht
# (Prioritätenliste, das erste vorhandene Feld gewinnt). "bescheinigung"
# fehlt bewusst: dort gibt es keine Beträge.
TAX_AMOUNT_FIELDS = {
    "lohnsteuerbescheinigung": ("income_tax",),
    "einkommensbescheinigung": ("settlement_amount", "income_tax"),
    "gehaltsabrechnung": ("net_amount", "gross_amount"),
}


def resolve_document_amount(document_type, data):
    """Betrag eines Dokuments für die Übersicht (generisch oder benannt)."""
    amount = normalize_amount(data.get("amount"))

    if amount is not None:
        return amount

    if document_type == TAX:
        fields = TAX_AMOUNT_FIELDS.get(data.get("document_subtype"), ())

        for field in fields:
            value = normalize_amount(data.get(field))

            if value is not None:
                return value

    return None


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
        # Beträge, deren Absetzbarkeit unklar ist (z. B. Versicherung ohne
        # erkannte Art) — separat ausweisen statt still mitsummieren.
        "deductible_unclear_amount": 0.0,
        "deductible_unclear_count": 0,
        # gezahlte Lohn-/Einkommensteuer (aus tax-Dokumenten)
        "income_tax": 0.0,
    }
    # Kapitalerträge (Anlage KAP), z. B. aus Bauspar-Jahresauszügen.
    capital_income = {"interest": 0.0, "capital_gains_tax": 0.0, "count": 0}

    for row in documents:
        if year_from_archive_path(row[2]) != year:
            continue

        document_type = row[3]
        category = tax_category_for_type(document_type)
        data = _parse_data(row[4])
        amount = resolve_document_amount(document_type, data)
        verified = bool(row[5])
        deductibility = document_deductibility(document_type, data)

        # Benannte Steuerfelder aufsummieren (unabhängig vom generischen amount).
        income_tax = normalize_amount(data.get("income_tax"))
        if income_tax is not None:
            totals["income_tax"] += income_tax

        # Nur die Steuerbescheinigung ist maßgeblich (aggregiert je Anbieter
        # über alle Verträge). Kontoauszüge würden sonst doppelt gezählt.
        if data.get("document_subtype") == "steuerbescheinigung":
            interest = normalize_amount(data.get("interest"))
            capital_gains_tax = normalize_amount(data.get("capital_gains_tax"))
            if interest is not None or capital_gains_tax is not None:
                capital_income["count"] += 1
                capital_income["interest"] += interest or 0.0
                capital_income["capital_gains_tax"] += capital_gains_tax or 0.0

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

            if deductibility == DEDUCTIBLE:
                totals["deductible_amount"] += amount

                if verified:
                    totals["deductible_verified_amount"] += amount

            elif deductibility == UNCLEAR:
                totals["deductible_unclear_amount"] += amount
                totals["deductible_unclear_count"] += 1

        entry["documents"].append(
            {
                "id": row[0],
                "filename": row[1],
                "document_type": document_type,
                "amount": amount,
                "verified": verified,
                "deductibility": deductibility,
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
        "capital_income": capital_income,
    }


def export_tax_summary_csv(summary):
    """Jahres-CSV je Dokument gemäß docs/05_Steuerlogik.md.

    Spalten: Datum, Kategorie, Betrag, Absetzbar, Geprueft, Dokumentreferenz.
    """
    deductibility_labels = {
        DEDUCTIBLE: "ja",
        NOT_DEDUCTIBLE: "nein",
        UNCLEAR: "unklar",
    }

    output = StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "Datum",
            "Kategorie",
            "Betrag",
            "Absetzbar",
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
                    deductibility_labels.get(document["deductibility"], "unklar"),
                    "ja" if document["verified"] else "nein",
                    document["filename"],
                ]
            )

    return output.getvalue()

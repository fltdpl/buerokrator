"""ELSTER-Anlagen-Zuordnung (framework-frei, testbar).

Berechnet je Steuerjahr die Positionen der Anlagen N, Vorsorgeaufwand und
KAP aus dem Dokumentbestand — siehe Zielbild in docs/05_Steuerlogik.md.

Grundregeln:
- In die Summen fließen NUR geprüfte UND steuerrelevante Dokumente.
  Passende, aber ungeprüfte Belege werden als To-do gelistet (`pending`),
  nie mitsummiert.
- Jede Position führt ihre Belege einzeln auf (Herleitung, keine Blackbox).
- Auffälligkeiten werden ausgewiesen statt verschluckt: geprüfte Belege
  ohne den erwarteten Wert (`missing_value`), Versicherungen mit unklarer
  Art (`unclear`).
"""

import json

from src.core.amount_utils import normalize_amount
from src.core.document_types import EMPLOYMENT, INSURANCE, PENSION
from src.database.list_documents import list_documents
from src.organizer.date_utils import year_from_archive_path
from src.tax.tax_relevance import resolve_tax_relevance
from src.tax.tax_summary import (
    DEDUCTIBLE,
    NOT_DEDUCTIBLE,
    document_deductibility,
)

# Status je Position (Ampel der Steuer-Seite).
READY = "ready"          # alle Belege geprüft, keine Auffälligkeiten
INCOMPLETE = "incomplete"  # ungeprüfte Belege vorhanden (zählen nicht)
UNCLEAR = "unclear"      # unklare Art / geprüfter Beleg ohne Wert
EMPTY = "empty"          # keine passenden Belege im Jahr

# Kranken-/Pflege-Beiträge aus Versicherungs-Bescheinigungen bekommen eine
# eigene Position mit Überschneidungs-Warnung: dieselben Beiträge können
# bereits auf der Lohnsteuerbescheinigung (Zeilen 25/26/28) stehen.
_HEALTH_KEYWORDS = ("kranken", "pflege")

# Positionen der Lohnsteuerbescheinigung: (Feld, Label, Anlage).
_LSTB_POSITIONS = (
    ("gross_amount", "Bruttoarbeitslohn (LStB Zeile 3)", "anlage_n"),
    ("income_tax", "Einbehaltene Lohnsteuer (LStB Zeile 4)", "anlage_n"),
    ("soli", "Einbehaltener Solidaritätszuschlag (LStB Zeile 5)", "anlage_n"),
    ("church_tax", "Einbehaltene Kirchensteuer (LStB Zeile 6/7)", "anlage_n"),
    (
        "pension_insurance_employer",
        "Rentenversicherung, Arbeitgeberanteil (LStB Zeile 22)",
        "vorsorgeaufwand",
    ),
    (
        "pension_insurance_employee",
        "Rentenversicherung, Arbeitnehmeranteil (LStB Zeile 23)",
        "vorsorgeaufwand",
    ),
    (
        "health_insurance",
        "Gesetzliche Krankenversicherung (LStB Zeile 25)",
        "vorsorgeaufwand",
    ),
    (
        "care_insurance",
        "Soziale Pflegeversicherung (LStB Zeile 26)",
        "vorsorgeaufwand",
    ),
    (
        "unemployment_insurance",
        "Arbeitslosenversicherung (LStB Zeile 27)",
        "vorsorgeaufwand",
    ),
    (
        "private_health_insurance",
        "Private Kranken-/Pflege-Pflichtversicherung (LStB Zeile 28)",
        "vorsorgeaufwand",
    ),
)

# Positionen der Anlage KAP aus pension/steuerbescheinigung.
_KAP_POSITIONS = (
    ("interest", "Kapitalerträge/Zinsen"),
    ("capital_gains_tax", "Einbehaltene Kapitalertragsteuer"),
    ("soli", "Solidaritätszuschlag auf Kapitalertragsteuer"),
    ("church_tax", "Kirchensteuer auf Kapitalertragsteuer"),
)

ANLAGE_LABELS = {
    "anlage_n": "Anlage N",
    "vorsorgeaufwand": "Anlage Vorsorgeaufwand",
    "kap": "Anlage KAP",
}


def _parse_data(raw):
    if not raw:
        return {}

    try:
        data = json.loads(raw)

    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _document_year(row, data):
    """Steuerjahr eines Dokuments: tax_year-Feld, sonst Archivjahr."""
    tax_year = data.get("tax_year")

    if tax_year is not None:
        try:
            return int(str(tax_year).strip())

        except (TypeError, ValueError):
            pass

    return year_from_archive_path(row["archive_path"])


def _reference(row, data, amount=None):
    """Beleg-Referenz für die Herleitung einer Position."""
    return {
        "id": row["id"],
        "filename": row["filename"],
        "issuer": (
            data.get("issuer")
            or data.get("insurer")
            or data.get("employer")
            or ""
        ),
        "amount": amount,
    }


def _new_position(key, label, hint=None):
    return {
        "key": key,
        "label": label,
        "amount": 0.0,
        "documents": [],
        "pending": [],
        "missing_value": [],
        "unclear": [],
        "hint": hint,
        "status": EMPTY,
    }


def _finalize_status(position):
    """Ampel: Auffälligkeit schlägt Unvollständigkeit schlägt Leere."""
    if position["unclear"] or position["missing_value"]:
        position["status"] = UNCLEAR

    elif position["pending"]:
        position["status"] = INCOMPLETE

    elif position["documents"]:
        position["status"] = READY

    else:
        position["status"] = EMPTY

    return position


def _field_positions(rows, positions_spec):
    """Feld-Positionen (LStB/KAP): pro Feld summieren + Belege sammeln.

    rows = [(row, data, verified)] der bereits nach Quelle/Jahr/Relevanz
    gefilterten Dokumente. Ungeprüfte landen in pending, geprüfte ohne
    den Feldwert in missing_value.
    """
    positions = []

    for spec in positions_spec:
        field, label = spec[0], spec[1]
        position = _new_position(field, label)

        for row, data, verified in rows:
            value = normalize_amount(data.get(field))

            if not verified:
                position["pending"].append(_reference(row, data, value))

            elif value is None:
                position["missing_value"].append(_reference(row, data))

            else:
                position["amount"] += value
                position["documents"].append(_reference(row, data, value))

        positions.append(_finalize_status(position))

    return positions


def build_elster_summary(year: int, documents: list[dict] | None = None) -> dict:
    """Anlagen-Positionen eines Steuerjahres mit Beleg-Herleitung."""
    if documents is None:
        documents = list_documents()

    lstb_rows = []
    kap_rows = []
    insurance_rows = []

    for row in documents:
        data = _parse_data(row["extracted_data"])

        if _document_year(row, data) != year:
            continue

        subtype = data.get("document_subtype")
        tax_relevant = resolve_tax_relevance(
            row["document_type"], data, row["tax_relevant"]
        )

        # Versicherungen mit UNKLARER Art sind per Default nicht steuerrelevant
        # (Relevanz-Default = absetzbar) — sie sollen aber als „unklar"
        # erscheinen statt still zu verschwinden. Nur ein explizites
        # Nutzer-Nein (tax_relevant = 0) filtert sie heraus.
        if row["document_type"] == INSURANCE:
            deductibility = document_deductibility(INSURANCE, data)
            unclear_kind = deductibility not in (DEDUCTIBLE, NOT_DEDUCTIBLE)

            if tax_relevant or (unclear_kind and row["tax_relevant"] is None):
                insurance_rows.append((row, data, bool(row["verified"])))

            continue

        if not tax_relevant:
            continue

        entry = (row, data, bool(row["verified"]))

        if row["document_type"] == EMPLOYMENT and subtype == "lohnsteuerbescheinigung":
            lstb_rows.append(entry)

        elif row["document_type"] == PENSION and subtype == "steuerbescheinigung":
            kap_rows.append(entry)

    lstb_positions = _field_positions(
        lstb_rows, [(f, l) for f, l, _ in _LSTB_POSITIONS]
    )
    positions_by_field = dict(zip((f for f, _, _ in _LSTB_POSITIONS), lstb_positions))

    anlage_n = [
        positions_by_field[field]
        for field, _, anlage in _LSTB_POSITIONS
        if anlage == "anlage_n"
    ]
    vorsorge = [
        positions_by_field[field]
        for field, _, anlage in _LSTB_POSITIONS
        if anlage == "vorsorgeaufwand"
    ]

    vorsorge.extend(_insurance_positions(insurance_rows))

    kap = _field_positions(kap_rows, _KAP_POSITIONS)

    return {
        "year": year,
        "anlagen": [
            {"key": "anlage_n", "label": ANLAGE_LABELS["anlage_n"], "positions": anlage_n},
            {
                "key": "vorsorgeaufwand",
                "label": ANLAGE_LABELS["vorsorgeaufwand"],
                "positions": vorsorge,
            },
            {"key": "kap", "label": ANLAGE_LABELS["kap"], "positions": kap},
        ],
    }


def _insurance_positions(rows):
    """Versicherungs-Positionen der Anlage Vorsorgeaufwand.

    Zwei Positionen: Kranken-/Pflege-Beiträge aus Bescheinigungen (mit
    Überschneidungs-Warnung zur LStB) und sonstige Vorsorge (Haftpflicht,
    Unfall, BU …). Unklare Versicherungsarten landen bei „sonstige" in
    unclear; nicht absetzbare (Hausrat …) werden ignoriert.
    """
    health = _new_position(
        "insurance_health",
        "Kranken-/Pflegebeiträge aus Beitragsbescheinigungen",
        hint=(
            "Achtung Überschneidung: Beiträge können bereits auf der "
            "Lohnsteuerbescheinigung (Zeilen 25/26/28) enthalten sein — "
            "nicht doppelt ansetzen."
        ),
    )
    other = _new_position(
        "insurance_other",
        "Sonstige Vorsorgeaufwendungen (Haftpflicht, Unfall, BU …)",
    )

    for row, data, verified in rows:
        deductibility = document_deductibility(INSURANCE, data)

        if deductibility == NOT_DEDUCTIBLE:
            continue

        amount = normalize_amount(data.get("amount"))
        insurance_type = str(data.get("insurance_type") or "").lower()
        is_health = any(keyword in insurance_type for keyword in _HEALTH_KEYWORDS)
        position = health if is_health else other

        if deductibility != DEDUCTIBLE:
            # Unklare Art: ausweisen statt still summieren oder verwerfen.
            position["unclear"].append(_reference(row, data, amount))

        elif not verified:
            position["pending"].append(_reference(row, data, amount))

        elif amount is None:
            position["missing_value"].append(_reference(row, data))

        else:
            position["amount"] += amount
            position["documents"].append(_reference(row, data, amount))

    return [_finalize_status(health), _finalize_status(other)]

import json

from src.core.document_types import (
    BANK,
    HOUSING,
    INSURANCE,
    INVOICE,
    LEGAL,
    PENSION,
    TAX,
)

# Kurzlabels je Subtyp — für die Dokumentenliste und den Detail-Header.
# Bewusst hier (core) gehalten, damit document_display keine Service-Schicht
# importiert; sie spiegeln die Labels aus services/form_schema.py.
TAX_SUBTYPE_SHORT_LABELS = {
    "lohnsteuerbescheinigung": "Lohnsteuer",
    "gehaltsabrechnung": "Gehaltsabrechnung",
    "einkommensbescheinigung": "Einkommensbescheinigung",
    "bescheinigung": "Bescheinigung",
}

PENSION_SUBTYPE_SHORT_LABELS = {
    "contract": "Vertrag",
    "annual_statement": "Jahresmitteilung",
    "cost_statement": "Kostenmitteilung",
    "surrender_value_table": "Rückkaufswerte",
    "pension_information": "Renteninformation",
    "bauspar_jahresauszug": "Bauspar-Jahresauszug",
    "steuerbescheinigung": "Steuerbescheinigung",
}

HOUSING_SUBTYPE_SHORT_LABELS = {
    "nebenkostenabrechnung": "Nebenkostenabrechnung",
    "mietvertrag": "Mietvertrag",
    "mieterhoehung": "Mieterhöhung",
    "hausgeldabrechnung": "Hausgeldabrechnung",
    "sonstiges": "Sonstiges",
}

BANK_SUBTYPE_SHORT_LABELS = {
    "kontoauszug": "Kontoauszug",
    "kreditkartenabrechnung": "Kreditkartenabrechnung",
    "depotuebersicht": "Depotübersicht",
    "sonstiges": "Sonstiges",
}


def _as_data(extracted_data):
    if isinstance(extracted_data, str):
        try:
            return json.loads(extracted_data)

        except Exception:
            return {}

    return extracted_data or {}


def get_document_art_label(document_type, extracted_data):
    """Kurzbezeichnung der Dokumentart bzw. -unterart (ohne Aussteller/Jahr).

    Für die Listenspalte „Dokument": nur die Art (z. B. „Nebenkostenabrechnung",
    „Vertrag", „Rechnung"). Fällt auf einen Typ-Standard zurück, wenn kein
    passender Subtyp erkannt ist.
    """
    data = _as_data(extracted_data)

    if document_type == INVOICE:
        return "Rechnung"

    if document_type == INSURANCE:
        return data.get("insurance_type") or "Versicherung"

    if document_type == TAX:
        subtype = data.get("document_subtype")
        if subtype == "bescheinigung":
            return data.get("description") or "Bescheinigung"

        return TAX_SUBTYPE_SHORT_LABELS.get(subtype, "Steuer")

    if document_type == PENSION:
        subtype = data.get("document_subtype")

        return (
            PENSION_SUBTYPE_SHORT_LABELS.get(subtype)
            or data.get("product_name")
            or "Vorsorge"
        )

    if document_type == HOUSING:
        subtype = data.get("document_subtype")
        if subtype == "sonstiges":
            return data.get("subject") or "Sonstiges"

        return HOUSING_SUBTYPE_SHORT_LABELS.get(subtype) or "Wohnen"

    if document_type == BANK:
        subtype = data.get("document_subtype")
        if subtype == "sonstiges":
            return data.get("subject") or "Sonstiges"

        return BANK_SUBTYPE_SHORT_LABELS.get(subtype) or "Bank"

    if document_type == LEGAL:
        return data.get("subject") or "Recht"

    return "Dokument"


def get_document_display_name(
    document_type,
    extracted_data,
    year=None,
):
    data = _as_data(extracted_data)

    issuer = (
        data.get("issuer") or data.get("insurer") or data.get("employer") or "Unbekannt"
    )

    issuer = issuer[:10]

    document_label = get_document_art_label(document_type, data)

    if year:
        return f"{year} · {issuer} · {document_label}"

    return f"{issuer} · {document_label}"

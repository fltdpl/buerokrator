from src.core.document_types import (
    BANK,
    HOUSING,
    INSURANCE,
    INVOICE,
    PENSION,
    TAX,
)

# Steuer-Subtypen und ihre jeweils gültigen Felder. Jeder Subtyp hat ein
# eigenes Feldset, damit nur passende Felder erfasst/gespeichert werden.
TAX_SUBTYPE_FIELDS = {
    # jährliche Lohnsteuerbescheinigung vom Arbeitgeber
    "lohnsteuerbescheinigung": {
        "document_subtype",
        "employer",
        "tax_year",
        "gross_amount",
        "income_tax",
        "soli",
        "church_tax",
    },
    # monatliche Gehalts-/Entgeltabrechnung vom Arbeitgeber
    "gehaltsabrechnung": {
        "document_subtype",
        "employer",
        "tax_year",
        "month",
        "gross_amount",
        "net_amount",
    },
    # Einkommensbescheinigung / Bescheid vom Finanzamt
    "einkommensbescheinigung": {
        "document_subtype",
        "issuer",
        "tax_year",
        "income_tax",
        "soli",
        "settlement_amount",
    },
}

# Erlaubte Felder je Dokumenttyp (muss dem jeweiligen Prompt-Schema entsprechen).
# Dient als Sicherheitsnetz: alles, was ein Modell darüber hinaus erfindet,
# wird verworfen, statt in die Datenbank zu gelangen.
ALLOWED_FIELDS = {
    INVOICE: {"issuer", "document_date", "invoice_number", "amount"},
    TAX: set().union(*TAX_SUBTYPE_FIELDS.values()),
    INSURANCE: {"issuer", "insurance_type", "policy_number", "document_date", "amount"},
    PENSION: {
        "issuer",
        "product_name",
        "policy_number",
        "document_date",
        "document_subtype",
        "amount",
    },
    BANK: {"issuer", "document_date", "document_subtype"},
    HOUSING: {"issuer", "document_date", "document_subtype"},
}


def whitelist_fields(document_type, data):
    """Reduziert ein Datendict auf die für den Dokumenttyp erlaubten Felder.

    Für Steuerdokumente wird zusätzlich nach document_subtype gefiltert, sodass
    beim Wechsel des Subtyps nicht mehr passende Felder verworfen werden. Für
    Typen ohne Schema (z. B. unknown) wird nicht gefiltert, um keinen
    unbeabsichtigten Datenverlust zu riskieren.
    """
    if not isinstance(data, dict):
        return {}

    if document_type == TAX:
        subtype = data.get("document_subtype")
        allowed = TAX_SUBTYPE_FIELDS.get(subtype, ALLOWED_FIELDS[TAX])
        return {key: value for key, value in data.items() if key in allowed}

    if document_type not in ALLOWED_FIELDS:
        return data

    allowed = ALLOWED_FIELDS[document_type]

    return {key: value for key, value in data.items() if key in allowed}

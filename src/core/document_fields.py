from src.core.document_types import (
    BANK,
    HOUSING,
    INSURANCE,
    INVOICE,
    PENSION,
    TAX,
)

# Erlaubte Felder je Dokumenttyp (muss dem jeweiligen Prompt-Schema entsprechen).
# Dient als Sicherheitsnetz: alles, was ein Modell darüber hinaus erfindet,
# wird verworfen, statt in die Datenbank zu gelangen.
ALLOWED_FIELDS = {
    INVOICE: {"issuer", "document_date", "invoice_number", "amount"},
    TAX: {
        "employer",
        "document_subtype",
        "tax_year",
        "month",
        "gross_amount",
        "income_tax",
        "soli",
        "church_tax",
        "net_amount",
    },
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

    Für Typen ohne definiertes Schema (z. B. unknown) wird nicht gefiltert,
    um kein unbeabsichtigtes Datenverlust zu riskieren.
    """
    if not isinstance(data, dict):
        return {}

    if document_type not in ALLOWED_FIELDS:
        return data

    allowed = ALLOWED_FIELDS[document_type]

    return {key: value for key, value in data.items() if key in allowed}

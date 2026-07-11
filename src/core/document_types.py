INVOICE = "invoice"
TAX = "tax"
INSURANCE = "insurance"
PENSION = "pension"
BANK = "bank"
HOUSING = "housing"
LEGAL = "legal"
UNKNOWN = "unknown"

DOCUMENT_TYPES = (
    INVOICE,
    TAX,
    INSURANCE,
    PENSION,
    BANK,
    HOUSING,
    LEGAL,
    UNKNOWN,
)

DOCUMENT_TYPE_SET = set(DOCUMENT_TYPES)

DOCUMENT_TYPE_LABELS = {
    INVOICE: "Rechnung",
    TAX: "Steuer",
    INSURANCE: "Versicherung",
    PENSION: "Vorsorge",
    BANK: "Bank",
    HOUSING: "Wohnen",
    LEGAL: "Recht",
    UNKNOWN: "Sonstiges",
}

ARCHIVE_CATEGORY_LABELS = {
    INVOICE: "Rechnungen",
    TAX: "Steuern",
    INSURANCE: "Versicherungen",
    PENSION: "Vorsorge",
    BANK: "Bank",
    HOUSING: "Wohnen",
    LEGAL: "Recht",
    UNKNOWN: "Sonstiges",
}


def normalize_document_type(document_type):
    if document_type in DOCUMENT_TYPE_SET:
        return document_type

    return UNKNOWN

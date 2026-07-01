from src.core.document_types import (
    HOUSING,
    INSURANCE,
    INVOICE,
    PENSION,
    TAX,
    UNKNOWN,
)

# Reihenfolge = Priorität: die erste passende Regel gewinnt.
RULES = (
    ("lohnsteuerbescheinigung", TAX),
    ("einkommensteuer", TAX),
    ("zahnarzt", INVOICE),
    ("versicherung", INSURANCE),
    ("bauspar", PENSION),
    ("nebenkostenabrechnung", HOUSING),
)


def classify(text):
    text = text.lower()

    for keyword, document_type in RULES:
        if keyword in text:
            return {"document_type": document_type}

    return {"document_type": UNKNOWN}

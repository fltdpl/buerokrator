from src.core.document_types import (
    HOUSING,
    INSURANCE,
    INVOICE,
    PENSION,
    TAX,
)

# Hochpräzise Schlüsselwörter, die eine LLM-Klassifikation überflüssig machen.
# Reihenfolge = Priorität: die erste passende Regel gewinnt. Steuer-/Lohn-
# Begriffe stehen bewusst zuerst, damit z. B. "Sozialversicherung" auf einer
# Gehaltsabrechnung nicht fälschlich als insurance erkannt wird.
RULES = (
    ("lohnsteuerbescheinigung", TAX),
    ("einkommensteuer", TAX),
    ("gehaltsabrechnung", TAX),
    ("entgeltabrechnung", TAX),
    ("lohnabrechnung", TAX),
    ("verdienstbescheinigung", TAX),
    ("einkommensbescheinigung", TAX),
    ("bezügemitteilung", TAX),
    ("bezuegemitteilung", TAX),
    ("zahnarzt", INVOICE),
    ("versicherung", INSURANCE),
    ("bauspar", PENSION),
    ("nebenkostenabrechnung", HOUSING),
)


def match_rule(text):
    """Gibt den Dokumenttyp zurück, wenn eine Regel greift, sonst None."""
    lowered = text.lower()

    for keyword, document_type in RULES:
        if keyword in lowered:
            return document_type

    return None

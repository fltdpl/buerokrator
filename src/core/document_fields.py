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
    # Auffangkategorie: Meldebescheinigungen (Sozialversicherung),
    # Informationsschreiben u. Ä. ohne eigene Beträge.
    "bescheinigung": {
        "document_subtype",
        "issuer",
        "tax_year",
        "description",
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
        # Bauspar-Jahresauszug / Kapitalerträge / Steuerbescheinigung
        "interest",
        "capital_gains_tax",
        "soli",
        "church_tax",
        "contributions_total",
        "opening_balance",
        "closing_balance",
    },
    BANK: {"issuer", "document_date", "document_subtype"},
    HOUSING: {"issuer", "document_date", "document_subtype", "amount"},
}

# Pension-Subtypen: der Bauspar-Jahresauszug nutzt Kapitalertragsfelder statt
# des generischen amount (Jahresbeitrag); alle anderen den Basissatz.
PENSION_BASE_FIELDS = {
    "issuer",
    "product_name",
    "policy_number",
    "document_date",
    "document_subtype",
    "amount",
}

PENSION_BAUSPAR_FIELDS = {
    "issuer",
    "product_name",
    "policy_number",
    "document_date",
    "document_subtype",
    "interest",
    "contributions_total",
    "opening_balance",
    "closing_balance",
}

PENSION_STEUERBESCHEINIGUNG_FIELDS = {
    "issuer",
    "product_name",
    "policy_number",
    "document_date",
    "document_subtype",
    "interest",
    "capital_gains_tax",
    "soli",
    "church_tax",
}

PENSION_SUBTYPE_FIELDS = {
    "bauspar_jahresauszug": PENSION_BAUSPAR_FIELDS,
    "steuerbescheinigung": PENSION_STEUERBESCHEINIGUNG_FIELDS,
}

# Kanonisches Subtyp-Vokabular je Dokumenttyp (muss Prompt + GUI-Labels
# entsprechen). Alles außerhalb wird beim Normalisieren auf einen Alias
# gemappt oder unverändert gelassen (kein Datenverlust).
KNOWN_SUBTYPES = {
    TAX: set(TAX_SUBTYPE_FIELDS),
    PENSION: {
        "contract",
        "annual_statement",
        "cost_statement",
        "surrender_value_table",
        "pension_information",
        "bauspar_jahresauszug",
        "steuerbescheinigung",
    },
    HOUSING: {
        "nebenkostenabrechnung",
        "mietvertrag",
        "mieterhoehung",
        "hausgeldabrechnung",
    },
    BANK: {
        "kontoauszug",
        "kreditkartenabrechnung",
        "depotuebersicht",
    },
}

# Aliasse für frei eingegebene oder vom LLM erfundene Subtypen.
SUBTYPE_ALIASES = {
    PENSION: {
        "bauspar-urkunde": "contract",
        "bauspar_urkunde": "contract",
        "vertrag": "contract",
        "jahresmitteilung": "annual_statement",
        "standmitteilung": "annual_statement",
        "kostenmitteilung": "cost_statement",
        "renteninformation": "pension_information",
        "jahreskontoauszug": "bauspar_jahresauszug",
        "kontoauszug": "bauspar_jahresauszug",
    },
    HOUSING: {
        "betriebskostenabrechnung": "nebenkostenabrechnung",
        "mieterhöhung": "mieterhoehung",
    },
    BANK: {
        "depotübersicht": "depotuebersicht",
    },
}


def normalize_subtype(document_type, value):
    """Normalisiert einen Subtyp auf das kanonische Vokabular.

    Kleinschreibung + Alias-Mapping; unbekannte Werte bleiben (kleingeschrieben)
    erhalten, damit nichts verloren geht.
    """
    if not isinstance(value, str) or not value.strip():
        return value

    lowered = value.strip().lower()
    return SUBTYPE_ALIASES.get(document_type, {}).get(lowered, lowered)


def whitelist_fields(document_type, data):
    """Reduziert ein Datendict auf die für den Dokumenttyp erlaubten Felder.

    Für Steuerdokumente wird zusätzlich nach document_subtype gefiltert, sodass
    beim Wechsel des Subtyps nicht mehr passende Felder verworfen werden. Für
    Typen ohne Schema (z. B. unknown) wird nicht gefiltert, um keinen
    unbeabsichtigten Datenverlust zu riskieren.
    """
    if not isinstance(data, dict):
        return {}

    if "document_subtype" in data:
        data = {
            **data,
            "document_subtype": normalize_subtype(
                document_type, data["document_subtype"]
            ),
        }

    if document_type == TAX:
        subtype = data.get("document_subtype")
        allowed = TAX_SUBTYPE_FIELDS.get(subtype, ALLOWED_FIELDS[TAX])
        return {key: value for key, value in data.items() if key in allowed}

    if document_type == PENSION:
        subtype = data.get("document_subtype")
        allowed = PENSION_SUBTYPE_FIELDS.get(subtype, PENSION_BASE_FIELDS)
        return {key: value for key, value in data.items() if key in allowed}

    if document_type not in ALLOWED_FIELDS:
        return data

    allowed = ALLOWED_FIELDS[document_type]

    return {key: value for key, value in data.items() if key in allowed}

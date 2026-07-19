from difflib import get_close_matches

from src.core.document_types import (
    BANK,
    EMPLOYMENT,
    HOUSING,
    INSURANCE,
    INVOICE,
    LEGAL,
    PENSION,
    TAX,
)

# Steuer-Subtypen und ihre jeweils gültigen Felder. Jeder Subtyp hat ein
# eigenes Feldset, damit nur passende Felder erfasst/gespeichert werden.
#
# Lohnsteuerbescheinigung und Gehaltsabrechnung sind in die Kategorie
# EMPLOYMENT ("Arbeit") umgezogen (Aussteller = Arbeitgeber, kein Steuer-,
# sondern Arbeits-Lebensbereich). Sie bleiben hier bewusst als Whitelist
# (nicht mehr im Formular, siehe form_schema) erhalten, damit noch nicht
# umsortierte Bestandsdokumente beim Speichern keine Felder verlieren.
TAX_SUBTYPE_FIELDS = {
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
    # Übergang: von tax nach employment gewandert (nur noch Whitelist).
    "lohnsteuerbescheinigung": {
        "document_subtype",
        "employer",
        "tax_year",
        "gross_amount",
        "income_tax",
        "soli",
        "church_tax",
    },
    "gehaltsabrechnung": {
        "document_subtype",
        "employer",
        "tax_year",
        "month",
        "gross_amount",
        "net_amount",
    },
}

# Arbeit-Subtypen. Die beiden Lohn-Subtypen behalten exakt die früheren
# tax-Felder, damit das Umsortieren von Bestandsdokumenten ein reiner
# Typwechsel ist (Feldwerte bleiben gültig). Vertrag/Kündigung/Zeugnis/
# Sonstiges tragen nur Aussteller, Datum und einen Freitext-Betreff.
EMPLOYMENT_SUBTYPE_FIELDS = {
    "lohnsteuerbescheinigung": {
        "document_subtype",
        "employer",
        "tax_year",
        # Bescheinigungszeitraum (vom–bis); unterscheidet mehrere
        # Teilzeit-Bescheinigungen desselben Jahres. tax_year bleibt maßgeblich
        # für die Jahres-Aggregation.
        "period_start",
        "period_end",
        "gross_amount",
        "income_tax",
        "soli",
        "church_tax",
        # Sozialversicherungsbeiträge (LStB Zeilen 22–27) — Grundlage der
        # Anlage Vorsorgeaufwand (siehe docs/05_Steuerlogik.md, Zielbild).
        "pension_insurance_employer",
        "pension_insurance_employee",
        "health_insurance",
        "care_insurance",
        "unemployment_insurance",
        "private_health_insurance",
        # Arbeitgeberleistungen (LStB Zeilen 17/18/20) — mindern bzw.
        # betreffen Werbungskosten (Entfernungspauschale, Verpflegung).
        "commuting_allowance_taxfree",
        "commuting_allowance_flat_taxed",
        "meal_allowance_taxfree",
    },
    # SV-Meldung (§ 25 DEÜV): Meldung zur Sozialversicherung vom Arbeitgeber,
    # inkl. Stornierungen. Nie steuerrelevant.
    "sv_meldung": {
        "document_subtype",
        "issuer",
        "period_start",
        "period_end",
        "subject",
    },
    "gehaltsabrechnung": {
        "document_subtype",
        "employer",
        "tax_year",
        # Abrechnungszeitraum (von–bis). "month" bleibt als Alt-Feld erhalten,
        # damit Bestandsabrechnungen beim Speichern nichts verlieren.
        "period_start",
        "period_end",
        "month",
        "gross_amount",
        "net_amount",
    },
    "arbeitsvertrag": {"document_subtype", "issuer", "document_date", "subject"},
    "kuendigung": {"document_subtype", "issuer", "document_date", "subject"},
    "arbeitszeugnis": {"document_subtype", "issuer", "document_date", "subject"},
    "sonstiges": {"document_subtype", "issuer", "document_date", "subject"},
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
    BANK: {"issuer", "document_date", "document_subtype", "subject"},
    HOUSING: {"issuer", "document_date", "document_subtype", "amount", "subject"},
    EMPLOYMENT: set().union(*EMPLOYMENT_SUBTYPE_FIELDS.values()),
    LEGAL: {"issuer", "document_date", "subject"},
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

# Bewusst OHNE policy_number: die Steuerbescheinigung aggregiert je Anbieter
# über alle Verträge — eine einzelne Vertragsnummer wäre irreführend (das LLM
# greift sonst Steuernummern o. Ä. ab).
PENSION_STEUERBESCHEINIGUNG_FIELDS = {
    "issuer",
    "product_name",
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
        "sonstiges",
    },
    BANK: {
        "kontoauszug",
        "kreditkartenabrechnung",
        "depotuebersicht",
        "sonstiges",
    },
    EMPLOYMENT: set(EMPLOYMENT_SUBTYPE_FIELDS),
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
    EMPLOYMENT: {
        "entgeltabrechnung": "gehaltsabrechnung",
        "entgeltnachweis": "gehaltsabrechnung",
        "lohnabrechnung": "gehaltsabrechnung",
        "verdienstbescheinigung": "gehaltsabrechnung",
        "bezügemitteilung": "gehaltsabrechnung",
        "bezuegemitteilung": "gehaltsabrechnung",
        "vertrag": "arbeitsvertrag",
        "kündigung": "kuendigung",
        "zeugnis": "arbeitszeugnis",
        "sozialversicherungsmeldung": "sv_meldung",
        "meldung zur sozialversicherung": "sv_meldung",
        "meldebescheinigung zur sozialversicherung": "sv_meldung",
        "deuev": "sv_meldung",
        "deüv": "sv_meldung",
    },
}


def normalize_subtype(document_type: str, value: object) -> object:
    """Normalisiert einen Subtyp auf das kanonische Vokabular.

    Kleinschreibung + Alias-Mapping; LLM-Tippfehler (z. B.
    "bauxpar_jahresauszug") werden per Ähnlichkeitsvergleich auf den nächsten
    bekannten Subtyp korrigiert. Unbekannte Werte bleiben (kleingeschrieben)
    erhalten, damit nichts verloren geht.
    """
    if not isinstance(value, str) or not value.strip():
        return value

    lowered = value.strip().lower()
    aliased = SUBTYPE_ALIASES.get(document_type, {}).get(lowered, lowered)

    known = KNOWN_SUBTYPES.get(document_type)
    if known and aliased not in known:
        close = get_close_matches(aliased, known, n=1, cutoff=0.85)
        if close:
            return close[0]

    return aliased


def whitelist_fields(document_type: str, data: dict | None) -> dict:
    """Reduziert ein Datendict auf die für den Dokumenttyp erlaubten Felder.

    Für Steuerdokumente wird zusätzlich nach document_subtype gefiltert, sodass
    beim Wechsel des Subtyps nicht mehr passende Felder verworfen werden. Für
    Typen ohne Schema (z. B. unknown) wird nicht gefiltert, um keinen
    unbeabsichtigten Datenverlust zu riskieren.
    """
    if not isinstance(data, dict):
        return {}

    # String-Werte trimmen: ein Leerzeichen am Ende (LLM oder Tippfehler im
    # Formular) hat schon Datumsfelder unparsebar gemacht — mit kaputten
    # Dateinamen als Folge ("…_bis_31.12.2019 _…").
    data = {
        key: value.strip() if isinstance(value, str) else value
        for key, value in data.items()
    }

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

    if document_type == EMPLOYMENT:
        subtype = data.get("document_subtype")
        allowed = EMPLOYMENT_SUBTYPE_FIELDS.get(subtype, ALLOWED_FIELDS[EMPLOYMENT])
        return {key: value for key, value in data.items() if key in allowed}

    if document_type not in ALLOWED_FIELDS:
        return data

    allowed = ALLOWED_FIELDS[document_type]

    return {key: value for key, value in data.items() if key in allowed}

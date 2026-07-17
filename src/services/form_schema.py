"""Framework-neutrale Formular-Schemata für die Dokument-Detailansicht.

Beschreibt deklarativ, welche Felder je Dokumenttyp (und ggf. Subtyp)
bearbeitbar sind. Frontends (Streamlit, NiceGUI) rendern nur noch dieses
Schema; die Feldauswahl selbst ist damit testbar und konsistent zur
Whitelist in `src/core/document_fields.py` (ein Test erzwingt das).

Feld-Spezifikation: {"key", "label", "kind", "required"} mit kind:
- "text": Freitext, wird unverändert übernommen
- "amount": Betragsfeld, wird beim Übernehmen mit normalize_amount geparst

`required` markiert Felder, ohne die ein Dokument für Archiv und Steuer
unbrauchbar ist. Es blockiert nichts — das Frontend hebt leere Pflichtfelder
beim Prüfen nur hervor (`missing_required_fields`), damit sie nicht
übersehen werden.
"""

from src.core.amount_utils import normalize_amount
from src.core.document_types import (
    BANK,
    EMPLOYMENT,
    HOUSING,
    INSURANCE,
    INVOICE,
    LEGAL,
    PENSION,
    TAX,
    UNKNOWN,
)

# Lohnsteuerbescheinigung und Gehaltsabrechnung sind in die Kategorie
# "Arbeit" (EMPLOYMENT) umgezogen — hier bleiben nur die Finanzamt- und
# Auffang-Subtypen.
TAX_SUBTYPE_LABELS = {
    "einkommensbescheinigung": "Einkommensbescheinigung (Finanzamt)",
    "bescheinigung": "Bescheinigung / Sonstiges",
}

EMPLOYMENT_SUBTYPE_LABELS = {
    "arbeitsvertrag": "Arbeitsvertrag",
    "kuendigung": "Kündigung",
    "arbeitszeugnis": "Zeugnis",
    "lohnsteuerbescheinigung": "Lohnsteuerbescheinigung (jährlich)",
    "gehaltsabrechnung": "Gehaltsabrechnung (monatlich)",
    "sv_meldung": "SV-Meldung (§ 25 DEÜV)",
    "sonstiges": "Sonstiges",
}

PENSION_SUBTYPE_LABELS = {
    "contract": "Vertrag",
    "annual_statement": "Jahresmitteilung",
    "cost_statement": "Kostenmitteilung",
    "surrender_value_table": "Rückkaufswerte",
    "pension_information": "Renteninformation",
    "bauspar_jahresauszug": "Bauspar-Jahresauszug",
    "steuerbescheinigung": "Steuerbescheinigung",
}

# Wohnen und Bank: der Subtyp kategorisiert nur (er ändert die Formularfelder
# nicht). "sonstiges" ist die Auffangkategorie für alles ohne eigene Art.
HOUSING_SUBTYPE_LABELS = {
    "nebenkostenabrechnung": "Nebenkostenabrechnung",
    "mietvertrag": "Mietvertrag",
    "mieterhoehung": "Mieterhöhung",
    "hausgeldabrechnung": "Hausgeldabrechnung",
    "sonstiges": "Sonstiges",
}

BANK_SUBTYPE_LABELS = {
    "kontoauszug": "Kontoauszug",
    "kreditkartenabrechnung": "Kreditkartenabrechnung",
    "depotuebersicht": "Depotübersicht",
    "sonstiges": "Sonstiges",
}


def _text(key, label, required=False):
    return {"key": key, "label": label, "kind": "text", "required": required}


def _amount(key, label, required=False):
    return {"key": key, "label": label, "kind": "amount", "required": required}


# Gemeinsame Felder aller Typen außer tax (tax hat eigene Felder je Subtyp).
# Aussteller und Datum sind Pflicht: aus ihnen entstehen Dateiname und
# Archivjahr.
_COMMON_FIELDS = (
    _text("issuer", "Aussteller", required=True),
    _text("document_date", "Datum", required=True),
)

_TYPE_FIELDS = {
    INVOICE: (
        _text("invoice_number", "Rechnungsnummer"),
        _amount("amount", "Betrag", required=True),
    ),
    INSURANCE: (
        _text("policy_number", "Versicherungsnummer"),
        _text("insurance_type", "Versicherungsart", required=True),
        _amount("amount", "Betrag (Jahresbeitrag)"),
    ),
    PENSION: (_text("product_name", "Produkt"),),
    HOUSING: (_amount("amount", "Betrag (Nachzahlung/Guthaben)"),),
}

# Auffangkategorie "sonstiges" (Wohnen/Bank) bzw. der Dokumenttyp "Sonstiges"
# (unknown) selbst: ohne eigene Beträge, deshalb braucht es eine
# Freitextangabe, WAS das Dokument ist (z. B. amtliche Meldebestätigung),
# sonst verschwindet diese Information im generischen Label.
_SUBJECT_FIELD = _text("subject", "Betreff")

_TYPE_FIELDS[UNKNOWN] = (_SUBJECT_FIELD,)

# Die Steuerbescheinigung aggregiert je Anbieter über alle Verträge und hat
# deshalb bewusst KEINE policy_number (siehe document_fields.py) — das Feld
# hier anzubieten hieße, Eingaben beim Speichern still zu verwerfen.
_PENSION_POLICY_FIELD = _text("policy_number", "Vertragsnummer")

# Pension: Subtypen mit Kapitalertragsfeldern statt generischem Jahresbeitrag.
_PENSION_SUBTYPE_FIELDS = {
    "bauspar_jahresauszug": (
        _amount("interest", "Guthabenszinsen"),
        _amount("contributions_total", "Beiträge (Jahressumme)"),
        _amount("opening_balance", "Saldovortrag"),
        _amount("closing_balance", "Endsaldo"),
    ),
    "steuerbescheinigung": (
        _amount("interest", "Kapitalerträge"),
        _amount("capital_gains_tax", "Kapitalertragssteuer"),
        _amount("soli", "Solidaritätszuschlag"),
        _amount("church_tax", "Kirchensteuer"),
    ),
}

_PENSION_DEFAULT_FIELDS = (_amount("amount", "Betrag (Jahresbeitrag)"),)

_TAX_SUBTYPE_FORM_FIELDS = {
    "einkommensbescheinigung": (
        _text("issuer", "Finanzamt", required=True),
        _amount("income_tax", "Einkommensteuer"),
        _amount("soli", "Solidaritätszuschlag"),
        _amount("settlement_amount", "Abrechnungsbetrag (Erstattung negativ)"),
    ),
    "bescheinigung": (
        _text("issuer", "Aussteller"),
        _text("description", "Art der Bescheinigung"),
    ),
}

# Arbeit: Lohn-Subtypen tragen Lohnfelder (Steuerjahr-basiert); die
# SV-Meldung Aussteller + Meldezeitraum + Betreff; Vertrag/Kündigung/Zeugnis/
# Sonstiges nur Aussteller, Datum und einen Freitext-Betreff.
_EMPLOYMENT_SUBTYPE_FORM_FIELDS = {
    "lohnsteuerbescheinigung": (
        _text("tax_year", "Steuerjahr", required=True),
        _text("employer", "Arbeitgeber", required=True),
        _text("period_start", "Bescheinigungszeitraum von"),
        _text("period_end", "Bescheinigungszeitraum bis"),
        _amount("gross_amount", "Bruttolohn", required=True),
        _amount("income_tax", "Lohnsteuer"),
        _amount("soli", "Solidaritätszuschlag"),
        _amount("church_tax", "Kirchensteuer"),
        # Sozialversicherungsbeiträge (LStB Zeilen 22–27) für die
        # Anlage Vorsorgeaufwand.
        _amount("pension_insurance_employer", "Rentenversicherung AG-Anteil (Z. 22)"),
        _amount("pension_insurance_employee", "Rentenversicherung AN-Anteil (Z. 23)"),
        _amount("health_insurance", "Krankenversicherung (Z. 25)"),
        _amount("care_insurance", "Pflegeversicherung (Z. 26)"),
        _amount("unemployment_insurance", "Arbeitslosenversicherung (Z. 27)"),
        _amount("private_health_insurance", "Private KV/PV (Z. 28)"),
    ),
    "gehaltsabrechnung": (
        _text("tax_year", "Steuerjahr", required=True),
        _text("employer", "Arbeitgeber", required=True),
        _text("period_start", "Abrechnungszeitraum von"),
        _text("period_end", "Abrechnungszeitraum bis"),
        _amount("gross_amount", "Bruttolohn", required=True),
        _amount("net_amount", "Nettolohn"),
    ),
    "sv_meldung": (
        _text("issuer", "Arbeitgeber", required=True),
        _text("period_start", "Meldezeitraum von"),
        _text("period_end", "Meldezeitraum bis"),
        _text("subject", "Betreff / Meldegrund"),
    ),
}

# Textbasierte Arbeit-Subtypen (Vertrag/Kündigung/Zeugnis/Sonstiges).
_EMPLOYMENT_TEXT_FIELDS = (
    _text("issuer", "Arbeitgeber", required=True),
    _text("document_date", "Datum", required=True),
    _text("subject", "Betreff"),
)


def subtype_config(document_type):
    """Subtyp-Auswahl für den Typ (Optionen + Labels) oder None.

    Frontends sollen unbekannte Bestandswerte in die Optionen aufnehmen,
    statt sie zu überschreiben (siehe is_known_subtype).
    """
    if document_type == TAX:
        return {
            "options": list(TAX_SUBTYPE_LABELS),
            "labels": TAX_SUBTYPE_LABELS,
        }

    if document_type == PENSION:
        return {
            "options": list(PENSION_SUBTYPE_LABELS),
            "labels": PENSION_SUBTYPE_LABELS,
        }

    if document_type == HOUSING:
        return {
            "options": list(HOUSING_SUBTYPE_LABELS),
            "labels": HOUSING_SUBTYPE_LABELS,
        }

    if document_type == BANK:
        return {
            "options": list(BANK_SUBTYPE_LABELS),
            "labels": BANK_SUBTYPE_LABELS,
        }

    if document_type == EMPLOYMENT:
        return {
            "options": list(EMPLOYMENT_SUBTYPE_LABELS),
            "labels": EMPLOYMENT_SUBTYPE_LABELS,
        }

    return None


def is_known_subtype(document_type, subtype):
    config = subtype_config(document_type)

    return bool(config) and subtype in config["options"]


def form_fields(document_type, subtype=None):
    """Bearbeitbare Felder für Typ (+ Subtyp), in Anzeige-Reihenfolge.

    Für tax mit unbekanntem Subtyp bewusst leer: keine falschen
    typspezifischen Felder anbieten; bestehende Werte bleiben erhalten.
    """
    if document_type == TAX:
        fields = [_text("tax_year", "Steuerjahr", required=True)]

        if is_known_subtype(TAX, subtype):
            fields.extend(_TAX_SUBTYPE_FORM_FIELDS[subtype])

        return fields

    if document_type == LEGAL:
        return [
            _text("issuer", "Korrespondenzpartner", required=True),
            _text("document_date", "Datum", required=True),
            _text("subject", "Betreff"),
        ]

    if document_type == EMPLOYMENT:
        # Lohn-Subtypen: Steuerjahr-basierte Lohnfelder (wie früher tax).
        # Alle anderen (auch unbekannte): Aussteller/Datum/Betreff.
        if subtype in _EMPLOYMENT_SUBTYPE_FORM_FIELDS:
            return list(_EMPLOYMENT_SUBTYPE_FORM_FIELDS[subtype])

        return list(_EMPLOYMENT_TEXT_FIELDS)

    fields = list(_COMMON_FIELDS)
    fields.extend(_TYPE_FIELDS.get(document_type, ()))

    if document_type == PENSION:
        if subtype != "steuerbescheinigung":
            fields.append(_PENSION_POLICY_FIELD)

        fields.extend(
            _PENSION_SUBTYPE_FIELDS.get(subtype, _PENSION_DEFAULT_FIELDS)
        )

    if document_type in (HOUSING, BANK) and subtype == "sonstiges":
        fields.append(_SUBJECT_FIELD)

    return fields


def is_empty_value(value):
    """Leer = nichts extrahiert. 0.0 ist ein Wert, keine Lücke."""
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    return False


def empty_fields(document_type, data, subtype=None):
    """Keys aller Formularfelder ohne Wert (für die Hervorhebung beim Prüfen)."""
    data = data if isinstance(data, dict) else {}

    return [
        field["key"]
        for field in form_fields(document_type, subtype)
        if is_empty_value(data.get(field["key"]))
    ]


def missing_required_fields(document_type, data, subtype=None):
    """Keys der leeren Pflichtfelder — Teilmenge von empty_fields."""
    data = data if isinstance(data, dict) else {}

    return [
        field["key"]
        for field in form_fields(document_type, subtype)
        if field.get("required") and is_empty_value(data.get(field["key"]))
    ]


def merge_form_values(document_type, data, values, subtype=None):
    """Übernimmt Formularwerte in die Dokumentdaten (framework-neutral).

    values: {feld_key: roher Widget-Wert}. Betragsfelder werden normalisiert
    (deutsche Schreibweise, leere Eingabe -> None), unbekannte Keys ignoriert.
    Nicht im Formular enthaltene Bestandsfelder bleiben unverändert (die
    Whitelist beim Speichern entfernt nicht mehr Passendes).
    """
    updated = dict(data) if isinstance(data, dict) else {}

    if subtype is not None:
        updated["document_subtype"] = subtype

    for field in form_fields(document_type, subtype):
        key = field["key"]

        if key not in values:
            continue

        if field["kind"] == "amount":
            updated[key] = normalize_amount(values[key])

        else:
            updated[key] = values[key]

    return updated

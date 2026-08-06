from src.core.document_fields import (
    KNOWN_SUBTYPES,
    constrain_subtype,
    normalize_subtype,
    whitelist_fields,
)
from src.core.document_types import BANK, EMPLOYMENT, HOUSING, PENSION, TAX


def test_aliases_map_to_canonical_values():
    assert normalize_subtype(PENSION, "Bauspar-Urkunde") == "contract"
    assert normalize_subtype(PENSION, "Jahreskontoauszug") == "bauspar_jahresauszug"
    assert normalize_subtype(HOUSING, "Nebenkostenabrechnung") == "nebenkostenabrechnung"
    assert normalize_subtype(HOUSING, "Betriebskostenabrechnung") == "nebenkostenabrechnung"


def test_llm_typos_fuzzy_corrected():
    assert normalize_subtype(PENSION, "bauxpar_jahresauszug") == "bauspar_jahresauszug"
    assert normalize_subtype(PENSION, "steuerbescheinigng") == "steuerbescheinigung"
    assert normalize_subtype(TAX, "lohnsteuerbescheingung") == "lohnsteuerbescheinigung"


def test_unknown_values_survive_lowercased():
    assert normalize_subtype(PENSION, "Sonderfall XY") == "sonderfall xy"
    assert normalize_subtype(TAX, None) is None
    assert normalize_subtype(TAX, "") == ""


def test_whitelist_normalizes_subtype():
    data = {"issuer": "Musterbau", "document_subtype": "Jahreskontoauszug", "interest": 5.0}
    result = whitelist_fields(PENSION, data)
    # Alias wird normalisiert UND das Feldset des Ziel-Subtyps greift
    assert result["document_subtype"] == "bauspar_jahresauszug"
    assert result["interest"] == 5.0


def test_whitelist_steuerbescheinigung_drops_policy_number():
    data = {
        "document_subtype": "steuerbescheinigung",
        "policy_number": "990001112223",
        "interest": 44.44,
    }
    result = whitelist_fields(PENSION, data)
    assert "policy_number" not in result
    assert result["interest"] == 44.44


def test_whitelist_housing_keeps_amount():
    data = {"issuer": "Hausverwaltung", "document_subtype": "nebenkostenabrechnung", "amount": 348.0}
    assert whitelist_fields(HOUSING, data)["amount"] == 348.0


def test_constrain_moves_invented_subtype_into_the_free_text_field():
    # Das Modell schreibt gelegentlich den Betreff in document_subtype. Daraus
    # entstünde eine Unterart, die es gar nicht gibt.
    data = {
        "issuer": "Musterbank AG",
        "document_subtype": "Allgemeine Geschäftsbedingungen",
        "subject": "",
    }

    result = constrain_subtype(BANK, data)

    assert result["document_subtype"] == "sonstiges"
    assert result["subject"] == "Allgemeine Geschäftsbedingungen"


def test_constrain_keeps_an_existing_free_text_value():
    data = {
        "document_subtype": "Saldenmitteilung",
        "subject": "Saldo zum Jahresende",
    }

    result = constrain_subtype(BANK, data)

    assert result["document_subtype"] == "sonstiges"
    assert result["subject"] == "Saldo zum Jahresende"


def test_constrain_leaves_known_subtypes_aliases_and_typos_alone():
    # Bekannte Werte, Aliasse und vom Ähnlichkeitsvergleich gedeckte Tippfehler
    # fasst constrain nicht an; kanonisch geschrieben werden sie erst in
    # whitelist_fields.
    for document_type, value in (
        (BANK, "Kontoauszug"),
        (HOUSING, "Betriebskostenabrechnung"),
        (EMPLOYMENT, "Entgeltabrechnung"),
        (PENSION, "bauxpar_jahresauszug"),
    ):
        data = {"document_subtype": value}

        assert constrain_subtype(document_type, data) == data


def test_constrain_uses_the_tax_catch_all_with_its_own_text_field():
    data = {"document_subtype": "Grundsteuermessbescheid", "tax_year": "2025"}

    result = constrain_subtype(TAX, data)

    assert result["document_subtype"] == "bescheinigung"
    assert result["description"] == "Grundsteuermessbescheid"


def test_constrain_empties_the_subtype_where_no_catch_all_exists():
    # pension kennt keine Auffangkategorie: lieber keine Unterart als eine
    # erfundene. Der Wortlaut steht weiterhin im Dokumenttext.
    result = constrain_subtype(PENSION, {"document_subtype": "Sonderfall XY"})

    assert result["document_subtype"] == ""


def test_constrain_ignores_empty_values_and_types_without_subtypes():
    assert constrain_subtype(BANK, {"document_subtype": ""}) == {"document_subtype": ""}
    assert constrain_subtype("invoice", {"document_subtype": "Mahnung"}) == {
        "document_subtype": "Mahnung"
    }
    assert constrain_subtype(BANK, None) == {}


def test_every_fallback_is_a_real_subtype_with_a_real_text_field():
    # Eine Auffangkategorie, die es im Vokabular oder im Formular nicht gibt,
    # erzeugte genau die Geister-Unterart, die sie verhindern soll.
    from src.core.document_fields import ALLOWED_FIELDS, SUBTYPE_FALLBACK
    from src.services.form_schema import is_known_subtype

    for document_type, (fallback, text_field) in SUBTYPE_FALLBACK.items():
        assert fallback in KNOWN_SUBTYPES[document_type]
        assert text_field in ALLOWED_FIELDS[document_type]
        assert is_known_subtype(document_type, fallback)


def test_heizkosten_aliases():
    from src.core.document_fields import normalize_subtype

    assert normalize_subtype("housing", "Heizkosten") == "heizkostenabrechnung"
    assert normalize_subtype("housing", "Heizkostenabrechnung") == "heizkostenabrechnung"

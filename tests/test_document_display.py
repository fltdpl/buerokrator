from src.core.document_display import (
    get_document_art_label,
    get_document_display_name,
)
from src.core.document_types import (
    BANK,
    EMPLOYMENT,
    HOUSING,
    INVOICE,
    LEGAL,
    PENSION,
    UNKNOWN,
)


def test_art_label_uses_housing_subtype():
    label = get_document_art_label(
        HOUSING, {"document_subtype": "nebenkostenabrechnung"}
    )
    assert label == "Nebenkostenabrechnung"


def test_art_label_falls_back_to_type_default():
    assert get_document_art_label(HOUSING, {}) == "Wohnen"
    assert get_document_art_label(BANK, {"document_subtype": "unbekannt"}) == "Bank"
    assert get_document_art_label(INVOICE, {}) == "Rechnung"


def test_art_label_pension_prefers_subtype_then_product():
    assert get_document_art_label(PENSION, {"document_subtype": "contract"}) == "Vertrag"
    assert get_document_art_label(PENSION, {"product_name": "Riester"}) == "Riester"
    assert get_document_art_label(PENSION, {}) == "Vorsorge"


def test_art_label_accepts_json_string():
    assert (
        get_document_art_label(HOUSING, '{"document_subtype": "mietvertrag"}')
        == "Mietvertrag"
    )


def test_art_label_uses_subject_for_sonstiges_and_legal():
    assert (
        get_document_art_label(
            HOUSING, {"document_subtype": "sonstiges", "subject": "Meldebestätigung"}
        )
        == "Meldebestätigung"
    )
    assert get_document_art_label(HOUSING, {"document_subtype": "sonstiges"}) == "Sonstiges"
    assert (
        get_document_art_label(LEGAL, {"subject": "Mahnbescheid"}) == "Mahnbescheid"
    )
    assert get_document_art_label(LEGAL, {}) == "Recht"
    assert get_document_art_label(UNKNOWN, {"subject": "Vereinssatzung"}) == "Vereinssatzung"
    assert get_document_art_label(UNKNOWN, {}) == "Sonstiges"


def test_art_label_employment_subtypes():
    assert (
        get_document_art_label(EMPLOYMENT, {"document_subtype": "arbeitsvertrag"})
        == "Arbeitsvertrag"
    )
    assert (
        get_document_art_label(EMPLOYMENT, {"document_subtype": "lohnsteuerbescheinigung"})
        == "Lohnsteuer"
    )
    assert (
        get_document_art_label(
            EMPLOYMENT, {"document_subtype": "sonstiges", "subject": "Bonusmitteilung"}
        )
        == "Bonusmitteilung"
    )
    assert get_document_art_label(EMPLOYMENT, {}) == "Arbeit"
    assert (
        get_document_art_label(
            EMPLOYMENT, {"document_subtype": "sv_meldung", "subject": "Stornierung"}
        )
        == "SV-Meldung · Stornierung"
    )
    assert (
        get_document_art_label(EMPLOYMENT, {"document_subtype": "sv_meldung"})
        == "SV-Meldung"
    )


def test_display_name_combines_year_issuer_and_art():
    name = get_document_display_name(
        HOUSING,
        {"issuer": "Hausverwaltung Meyer", "document_subtype": "mietvertrag"},
        year=2024,
    )
    # Aussteller wird auf 10 Zeichen gekürzt.
    assert name == "2024 · Hausverwal · Mietvertrag"

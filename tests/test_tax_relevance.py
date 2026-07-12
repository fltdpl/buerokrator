from src.core.document_types import (
    BANK,
    EMPLOYMENT,
    INSURANCE,
    LEGAL,
    PENSION,
    TAX,
)
from src.tax.tax_relevance import default_tax_relevance, resolve_tax_relevance


def test_default_employment_only_salary_documents():
    assert default_tax_relevance(EMPLOYMENT, {"document_subtype": "lohnsteuerbescheinigung"})
    assert default_tax_relevance(EMPLOYMENT, {"document_subtype": "gehaltsabrechnung"})
    assert not default_tax_relevance(EMPLOYMENT, {"document_subtype": "arbeitsvertrag"})
    assert not default_tax_relevance(EMPLOYMENT, {"document_subtype": "kuendigung"})


def test_default_tax_and_pension():
    assert default_tax_relevance(TAX, {"document_subtype": "einkommensbescheinigung"})
    assert not default_tax_relevance(TAX, {"document_subtype": "bescheinigung"})
    assert default_tax_relevance(PENSION, {"document_subtype": "steuerbescheinigung"})
    assert not default_tax_relevance(PENSION, {"document_subtype": "contract"})


def test_default_insurance_uses_deductibility():
    assert default_tax_relevance(INSURANCE, {"insurance_type": "Krankenversicherung"})
    assert not default_tax_relevance(INSURANCE, {"insurance_type": "Hausratversicherung"})
    # Unbekannte Art ist nicht "deductible" -> Default nicht relevant.
    assert not default_tax_relevance(INSURANCE, {})


def test_default_other_types_are_not_relevant():
    assert not default_tax_relevance(BANK, {})
    assert not default_tax_relevance(LEGAL, {})


def test_resolve_prefers_stored_value_over_default():
    data = {"document_subtype": "arbeitsvertrag"}

    # Default wäre False; gespeicherte 1 überstimmt.
    assert resolve_tax_relevance(EMPLOYMENT, data, 1) is True
    # Gespeicherte 0 überstimmt einen True-Default.
    assert (
        resolve_tax_relevance(
            EMPLOYMENT, {"document_subtype": "lohnsteuerbescheinigung"}, 0
        )
        is False
    )
    # None -> Default greift.
    assert resolve_tax_relevance(EMPLOYMENT, data, None) is False

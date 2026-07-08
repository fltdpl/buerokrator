from src.core.document_fields import whitelist_fields
from src.core.document_types import (
    BANK,
    HOUSING,
    INSURANCE,
    INVOICE,
    PENSION,
    TAX,
)
from src.services.form_schema import (
    PENSION_SUBTYPE_LABELS,
    TAX_SUBTYPE_LABELS,
    form_fields,
    is_known_subtype,
    merge_form_values,
    subtype_config,
)

ALL_TYPE_SUBTYPE_COMBINATIONS = [
    (INVOICE, None),
    (INSURANCE, None),
    (BANK, None),
    (HOUSING, None),
    *[(TAX, subtype) for subtype in TAX_SUBTYPE_LABELS],
    *[(PENSION, subtype) for subtype in PENSION_SUBTYPE_LABELS],
]


def test_all_form_fields_survive_the_whitelist():
    """Jedes Formularfeld muss von der Whitelist akzeptiert werden — sonst
    verwirft das Speichern still, was der Benutzer eingegeben hat."""
    for document_type, subtype in ALL_TYPE_SUBTYPE_COMBINATIONS:
        fields = form_fields(document_type, subtype)
        data = {field["key"]: "x" for field in fields}

        if subtype is not None:
            data["document_subtype"] = subtype

        kept = whitelist_fields(document_type, data)

        for field in fields:
            assert field["key"] in kept, (
                f"{document_type}/{subtype}: Feld '{field['key']}' würde "
                "beim Speichern verworfen (Whitelist prüfen)"
            )


def test_subtype_config_matches_labels():
    tax = subtype_config(TAX)
    assert tax["options"] == list(TAX_SUBTYPE_LABELS)

    pension = subtype_config(PENSION)
    assert pension["options"] == list(PENSION_SUBTYPE_LABELS)

    assert subtype_config(INVOICE) is None


def test_tax_unknown_subtype_offers_only_tax_year():
    fields = form_fields(TAX, "voellig_unbekannt")

    assert [field["key"] for field in fields] == ["tax_year"]
    assert not is_known_subtype(TAX, "voellig_unbekannt")


def test_pension_unknown_subtype_falls_back_to_amount():
    keys = [field["key"] for field in form_fields(PENSION, "irgendwas")]

    assert "amount" in keys
    assert "interest" not in keys


def test_pension_bauspar_uses_capital_fields_instead_of_amount():
    keys = [field["key"] for field in form_fields(PENSION, "bauspar_jahresauszug")]

    assert "amount" not in keys
    assert {"interest", "contributions_total", "opening_balance", "closing_balance"} <= set(keys)


def test_merge_form_values_normalizes_amounts_and_keeps_rest():
    data = {"issuer": "Alt", "policy_number": "P-1", "custom": "bleibt"}

    updated = merge_form_values(
        INSURANCE,
        data,
        {
            "issuer": "Neu",
            "amount": "1.234,56",
            "insurance_type": "Haftpflichtversicherung",
        },
    )

    assert updated["issuer"] == "Neu"
    assert updated["amount"] == 1234.56
    assert updated["insurance_type"] == "Haftpflichtversicherung"
    # Nicht im Formular enthaltene Bestandswerte bleiben unverändert.
    assert updated["policy_number"] == "P-1"
    assert updated["custom"] == "bleibt"
    # Original nicht mutiert.
    assert data["issuer"] == "Alt"


def test_merge_form_values_sets_subtype_and_empty_amount_is_none():
    updated = merge_form_values(
        TAX,
        {},
        {"tax_year": "2024", "income_tax": ""},
        subtype="lohnsteuerbescheinigung",
    )

    assert updated["document_subtype"] == "lohnsteuerbescheinigung"
    assert updated["tax_year"] == "2024"
    assert updated["income_tax"] is None

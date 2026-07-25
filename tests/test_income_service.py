"""Jahreseinkommen aus Lohnsteuerbescheinigungen. Alle Zahlen erfunden."""

from src.services.income_service import build_income_series
from tests.test_elster_mapping import lstb, make_row


def test_single_lstb_yields_brutto_steuern_und_rechnerisches_netto():
    docs = [
        lstb(
            1,
            year=2024,
            gross_amount=38500.0,
            income_tax=5120.0,
            soli=0.0,
            church_tax=410.5,
            pension_insurance_employee=3580.5,
            health_insurance=2810.0,
            care_insurance=655.25,
            unemployment_insurance=500.5,
        )
    ]

    (entry,) = build_income_series(docs)

    assert entry["year"] == 2024
    assert entry["brutto"] == 38500.0
    assert entry["steuern"] == 5530.5  # 5120 + 0 + 410.5
    # Netto = 38500 − 5530.5 − (3580.5 + 2810 + 655.25 + 500.5)
    assert round(entry["netto"], 2) == 25423.25
    assert [ref["id"] for ref in entry["documents"]] == [1]


def test_two_lstb_same_year_add_up():
    # Teilzeit/Arbeitgeberwechsel: zwei Bescheinigungen desselben Jahres.
    docs = [
        lstb(1, year=2024, gross_amount=12000.0, income_tax=900.0),
        lstb(2, year=2024, gross_amount=18000.0, income_tax=1600.0),
    ]

    (entry,) = build_income_series(docs)

    assert entry["brutto"] == 30000.0
    assert entry["steuern"] == 2500.0
    assert len(entry["documents"]) == 2


def test_unverified_lstb_is_pending_not_counted():
    docs = [
        lstb(1, year=2024, gross_amount=30000.0),
        lstb(2, year=2024, verified=0, gross_amount=99999.0),
    ]

    (entry,) = build_income_series(docs)

    assert entry["brutto"] == 30000.0
    assert [ref["id"] for ref in entry["pending"]] == [2]


def test_verified_lstb_without_gross_is_reported_not_summed():
    docs = [lstb(1, year=2024, income_tax=1000.0)]

    (entry,) = build_income_series(docs)

    assert entry["brutto"] == 0.0
    assert entry["documents"] == []
    assert [ref["id"] for ref in entry["missing_value"]] == [1]


def test_gap_years_are_absent_not_zero():
    docs = [
        lstb(1, year=2021, gross_amount=28000.0),
        lstb(2, year=2023, gross_amount=31000.0),
    ]

    series = build_income_series(docs)

    assert [entry["year"] for entry in series] == [2021, 2023]


def test_other_document_types_and_irrelevant_lstb_are_ignored():
    docs = [
        lstb(1, year=2024, gross_amount=30000.0),
        # Explizit nicht steuerrelevant markiert (z. B. Duplikat).
        {
            **lstb(2, year=2024, gross_amount=30000.0),
            "tax_relevant": 0,
        },
        # Gehaltsabrechnung zählt nicht (redundant zur LStB).
        make_row(
            3,
            "employment",
            2024,
            {"document_subtype": "gehaltsabrechnung", "gross_amount": 2500.0},
        ),
        make_row(4, "invoice", 2024, {"amount": 99.0}),
    ]

    (entry,) = build_income_series(docs)

    assert entry["brutto"] == 30000.0
    assert len(entry["documents"]) == 1


def test_year_falls_back_to_archive_path():
    row = lstb(1, year=2022, gross_amount=20000.0)
    data = row["extracted_data"].replace('"tax_year": "2022", ', "")
    row["extracted_data"] = data
    assert "tax_year" not in data

    (entry,) = build_income_series([row])

    assert entry["year"] == 2022  # aus archive/2022/…

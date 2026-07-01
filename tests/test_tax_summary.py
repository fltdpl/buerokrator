import json

from src.tax.tax_summary import (
    available_tax_years,
    build_tax_summary,
    export_tax_summary_csv,
    tax_category_for_type,
)


def make_row(
    document_id,
    document_type,
    year,
    extracted_data,
    verified=0,
    category_folder="Kategorie",
):
    filename = f"{year}-01-01_dok.pdf"
    archive_path = f"archive/{year}/{category_folder}/{filename}"

    return (
        document_id,
        filename,
        archive_path,
        document_type,
        json.dumps(extracted_data),
        verified,
        f"{year}-01-01T00:00:00",
        "text",
        "",
    )


def sample_documents():
    return [
        make_row(1, "insurance", 2019, {"amount": 300.0, "document_date": "01.06.2019"}, verified=1),
        make_row(2, "insurance", 2019, {"amount": "120,50"}, verified=0),
        make_row(3, "pension", 2019, {"amount": 1200.0}, verified=1),
        make_row(4, "invoice", 2019, {"amount": 42.5}, verified=1),
        make_row(5, "insurance", 2020, {"amount": 400.0}, verified=1),
        make_row(6, "tax", 2019, {"tax_year": "2019", "employer": "ACME"}, verified=0),
    ]


def test_tax_category_mapping():
    assert tax_category_for_type("insurance") == "vorsorgeaufwendungen"
    assert tax_category_for_type("pension") == "altersvorsorge"
    assert tax_category_for_type("does-not-exist") == "sonstiges"


def test_available_tax_years():
    assert available_tax_years(sample_documents()) == [2019, 2020]


def test_build_tax_summary_filters_by_year():
    summary = build_tax_summary(2019, sample_documents())

    assert summary["year"] == 2019
    # Dokument aus 2020 darf nicht enthalten sein.
    assert summary["totals"]["count"] == 5


def test_build_tax_summary_sums_and_verified_split():
    summary = build_tax_summary(2019, sample_documents())

    by_category = {c["category"]: c for c in summary["categories"]}

    vorsorge = by_category["vorsorgeaufwendungen"]
    # 300 (geprüft) + 120.50 (ungeprüft)
    assert vorsorge["count"] == 2
    assert vorsorge["amount"] == 420.5
    assert vorsorge["verified_amount"] == 300.0
    assert vorsorge["deductible"] is True

    # Absetzbare Summen: nur Vorsorgeaufwendungen zählen.
    assert summary["totals"]["deductible_amount"] == 420.5
    assert summary["totals"]["deductible_verified_amount"] == 300.0


def test_build_tax_summary_category_order():
    summary = build_tax_summary(2019, sample_documents())

    order = [c["category"] for c in summary["categories"]]
    # Steuerlich relevante Kategorien zuerst.
    assert order[0] == "vorsorgeaufwendungen"
    assert order.index("vorsorgeaufwendungen") < order.index("rechnungen")


def test_export_tax_summary_csv_has_header_and_rows():
    summary = build_tax_summary(2019, sample_documents())
    csv_text = export_tax_summary_csv(summary)

    lines = [line for line in csv_text.splitlines() if line]

    assert lines[0] == "Datum;Kategorie;Betrag;Geprueft;Dokumentreferenz"
    # Eine Zeile pro Dokument des Jahres (5 Dokumente 2019).
    assert len(lines) == 1 + 5

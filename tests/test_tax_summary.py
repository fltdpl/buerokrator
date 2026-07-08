import json

from src.tax.tax_summary import (
    available_tax_years,
    build_tax_summary,
    export_tax_summary_csv,
    resolve_document_amount,
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


def test_resolve_document_amount_uses_named_tax_fields():
    # Generisches amount hat Vorrang.
    assert resolve_document_amount("invoice", {"amount": 42.5}) == 42.5

    # tax: benannte Felder je Subtyp.
    assert resolve_document_amount(
        "tax",
        {"document_subtype": "lohnsteuerbescheinigung", "income_tax": 8000.0},
    ) == 8000.0
    # settlement_amount behält sein Vorzeichen (Erstattung negativ).
    assert resolve_document_amount(
        "tax",
        {
            "document_subtype": "einkommensbescheinigung",
            "settlement_amount": -350.0,
            "income_tax": 9000.0,
        },
    ) == -350.0
    assert resolve_document_amount(
        "tax",
        {"document_subtype": "gehaltsabrechnung", "gross_amount": 4000.0},
    ) == 4000.0
    assert resolve_document_amount(
        "tax",
        {
            "document_subtype": "gehaltsabrechnung",
            "net_amount": 2500.0,
            "gross_amount": 4000.0,
        },
    ) == 2500.0

    # Ohne Beträge bzw. bei Subtypen ohne Betragsfelder: None.
    assert resolve_document_amount(
        "tax", {"document_subtype": "bescheinigung"}
    ) is None
    assert resolve_document_amount("tax", {}) is None


def test_build_tax_summary_sums_named_tax_amounts():
    docs = [
        make_row(
            1,
            "tax",
            2023,
            {"document_subtype": "lohnsteuerbescheinigung", "income_tax": 8000.0},
            verified=1,
        ),
        make_row(
            2,
            "tax",
            2023,
            {"document_subtype": "bescheinigung", "issuer": "Krankenkasse"},
            verified=1,
        ),
    ]

    summary = build_tax_summary(2023, docs)
    by_category = {c["category"]: c for c in summary["categories"]}

    einkommen = by_category["einkommen"]
    assert einkommen["count"] == 2
    assert einkommen["amount"] == 8000.0
    assert einkommen["verified_amount"] == 8000.0


def test_capital_income_counts_only_steuerbescheinigung():
    docs = [
        make_row(
            1,
            "pension",
            2023,
            {
                "document_subtype": "steuerbescheinigung",
                "interest": 120.0,
                "capital_gains_tax": 30.0,
            },
        ),
        # Bauspar-Kontoauszug: darf NICHT in die Kapitalerträge-Summe zählen.
        make_row(
            2,
            "pension",
            2023,
            {"document_subtype": "bauspar_jahresauszug", "interest": 999.0},
        ),
        make_row(
            3,
            "tax",
            2023,
            {"document_subtype": "lohnsteuerbescheinigung", "income_tax": 8000.0},
        ),
    ]

    summary = build_tax_summary(2023, docs)

    assert summary["capital_income"]["count"] == 1
    assert summary["capital_income"]["interest"] == 120.0
    assert summary["capital_income"]["capital_gains_tax"] == 30.0
    assert summary["totals"]["income_tax"] == 8000.0

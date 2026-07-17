"""ELSTER-Anlagen-Zuordnung: Summen, Herleitung, Ampel.

Alle Zahlen sind erfunden.
"""

import json

from src.tax.elster_mapping import (
    EMPTY,
    INCOMPLETE,
    READY,
    UNCLEAR,
    build_elster_summary,
)


def make_row(
    id,
    document_type,
    year,
    data,
    verified=1,
    tax_relevant=None,
):
    return {
        "id": id,
        "filename": f"dok_{id}.pdf",
        "archive_path": f"archive/{year}/Kategorie/dok_{id}.pdf",
        "document_type": document_type,
        "extracted_data": json.dumps(data),
        "verified": verified,
        "tax_relevant": tax_relevant,
    }


def lstb(id, year=2025, verified=1, **fields):
    data = {
        "document_subtype": "lohnsteuerbescheinigung",
        "employer": "Musterfirma GmbH",
        "tax_year": str(year),
        **fields,
    }
    return make_row(id, "employment", year, data, verified=verified)


def positions(summary, anlage_key):
    (anlage,) = [a for a in summary["anlagen"] if a["key"] == anlage_key]
    return {p["key"]: p for p in anlage["positions"]}


def test_lstb_fills_anlage_n_and_vorsorgeaufwand():
    docs = [
        lstb(
            1,
            gross_amount=38500.0,
            income_tax=5120.0,
            soli=0.0,
            church_tax=410.5,
            pension_insurance_employer=3580.5,
            pension_insurance_employee=3580.5,
            health_insurance=2810.25,
            care_insurance=655.75,
            unemployment_insurance=500.5,
            private_health_insurance=307.0,
        ),
    ]

    summary = build_elster_summary(2025, docs)

    anlage_n = positions(summary, "anlage_n")
    assert anlage_n["gross_amount"]["amount"] == 38500.0
    assert anlage_n["income_tax"]["amount"] == 5120.0
    assert anlage_n["soli"]["amount"] == 0.0
    assert anlage_n["church_tax"]["amount"] == 410.5
    assert anlage_n["gross_amount"]["status"] == READY

    vorsorge = positions(summary, "vorsorgeaufwand")
    assert vorsorge["pension_insurance_employee"]["amount"] == 3580.5
    assert vorsorge["private_health_insurance"]["amount"] == 307.0
    # Herleitung: der Beleg ist einzeln aufgeführt.
    assert vorsorge["health_insurance"]["documents"] == [
        {
            "id": 1,
            "filename": "dok_1.pdf",
            "issuer": "Musterfirma GmbH",
            "amount": 2810.25,
        }
    ]


def test_two_partial_lstb_of_same_year_add_up():
    docs = [
        lstb(1, gross_amount=12000.0, income_tax=900.0),
        lstb(2, gross_amount=20000.0, income_tax=2100.0),
    ]

    summary = build_elster_summary(2025, docs)
    anlage_n = positions(summary, "anlage_n")

    assert anlage_n["gross_amount"]["amount"] == 32000.0
    assert len(anlage_n["gross_amount"]["documents"]) == 2


def test_unverified_lstb_is_pending_and_never_summed():
    docs = [
        lstb(1, gross_amount=12000.0),
        lstb(2, gross_amount=99999.0, verified=0),
    ]

    summary = build_elster_summary(2025, docs)
    position = positions(summary, "anlage_n")["gross_amount"]

    assert position["amount"] == 12000.0
    assert [ref["id"] for ref in position["pending"]] == [2]
    assert position["status"] == INCOMPLETE


def test_verified_lstb_without_field_is_flagged():
    # Bestand von vor der SV-Feld-Erweiterung: geprüft, aber ohne Zeile 23.
    docs = [lstb(1, gross_amount=12000.0)]

    summary = build_elster_summary(2025, docs)
    position = positions(summary, "vorsorgeaufwand")["pension_insurance_employee"]

    assert position["amount"] == 0.0
    assert [ref["id"] for ref in position["missing_value"]] == [1]
    assert position["status"] == UNCLEAR


def test_gehaltsabrechnungen_do_not_count():
    # Doppelzählungs-Falle: 12 Monatsabrechnungen sind per Default nicht
    # steuerrelevant und tauchen nirgends auf.
    docs = [
        make_row(
            month,
            "employment",
            2025,
            {
                "document_subtype": "gehaltsabrechnung",
                "tax_year": "2025",
                "gross_amount": 3100.0,
                "income_tax": 420.0,
            },
        )
        for month in range(1, 13)
    ] + [lstb(20, gross_amount=37200.0, income_tax=5040.0)]

    summary = build_elster_summary(2025, docs)
    position = positions(summary, "anlage_n")["income_tax"]

    assert position["amount"] == 5040.0
    assert len(position["documents"]) == 1
    assert position["pending"] == []


def test_kap_only_from_steuerbescheinigung():
    # Doppelzählungs-Falle: der Bauspar-Jahresauszug trägt dieselben Zinsen.
    docs = [
        make_row(
            1,
            "pension",
            2025,
            {
                "document_subtype": "steuerbescheinigung",
                "issuer": "Musterbank",
                "interest": 210.4,
                "capital_gains_tax": 52.6,
            },
        ),
        make_row(
            2,
            "pension",
            2025,
            {
                "document_subtype": "bauspar_jahresauszug",
                "issuer": "Musterbausparkasse",
                "interest": 210.4,
            },
        ),
    ]

    summary = build_elster_summary(2025, docs)
    kap = positions(summary, "kap")

    assert kap["interest"]["amount"] == 210.4
    assert [ref["id"] for ref in kap["interest"]["documents"]] == [1]
    assert kap["capital_gains_tax"]["amount"] == 52.6


def test_insurance_split_health_vs_other_and_hint():
    docs = [
        make_row(
            1,
            "insurance",
            2025,
            {"insurance_type": "Haftpflichtversicherung", "amount": 89.9},
        ),
        make_row(
            2,
            "insurance",
            2025,
            {"insurance_type": "Krankenversicherung", "amount": 1234.5},
        ),
        # Nicht absetzbar: taucht nirgends auf.
        make_row(
            3,
            "insurance",
            2025,
            {"insurance_type": "Hausratversicherung", "amount": 120.0},
        ),
    ]

    summary = build_elster_summary(2025, docs)
    vorsorge = positions(summary, "vorsorgeaufwand")

    other = vorsorge["insurance_other"]
    assert other["amount"] == 89.9
    assert other["status"] == READY

    health = vorsorge["insurance_health"]
    assert health["amount"] == 1234.5
    # Überschneidungs-Warnung zur LStB (Zeilen 25/26/28).
    assert "nicht doppelt" in health["hint"]

    all_ids = {
        ref["id"]
        for position in vorsorge.values()
        for ref in position["documents"] + position["pending"] + position["unclear"]
    }
    assert 3 not in all_ids


def test_unclear_insurance_is_listed_not_dropped():
    # Unklare Art ist per Default nicht steuerrelevant — sie muss trotzdem
    # als „unklar" erscheinen, sonst verschwindet der Betrag unsichtbar.
    docs = [make_row(1, "insurance", 2025, {"amount": 300.0})]

    summary = build_elster_summary(2025, docs)
    position = positions(summary, "vorsorgeaufwand")["insurance_other"]

    assert position["amount"] == 0.0
    assert [ref["id"] for ref in position["unclear"]] == [1]
    assert position["status"] == UNCLEAR


def test_explicit_not_tax_relevant_excludes_document():
    docs = [
        make_row(
            1,
            "insurance",
            2025,
            {"insurance_type": "Haftpflichtversicherung", "amount": 89.9},
            tax_relevant=0,
        ),
        # Auch unklare Art: explizites Nutzer-Nein gewinnt.
        make_row(2, "insurance", 2025, {"amount": 300.0}, tax_relevant=0),
    ]

    summary = build_elster_summary(2025, docs)
    position = positions(summary, "vorsorgeaufwand")["insurance_other"]

    assert position["amount"] == 0.0
    assert position["unclear"] == []
    assert position["status"] == EMPTY


def test_year_filter_uses_tax_year_with_archive_fallback():
    docs = [
        # tax_year-Feld gewinnt über das Archivjahr.
        make_row(
            1,
            "employment",
            2026,  # Archivpfad 2026 …
            {
                "document_subtype": "lohnsteuerbescheinigung",
                "tax_year": "2025",  # … aber Steuerjahr 2025
                "gross_amount": 11000.0,
            },
        ),
        # Ohne tax_year zählt das Archivjahr.
        make_row(
            2,
            "insurance",
            2025,
            {"insurance_type": "Unfallversicherung", "amount": 150.0},
        ),
        # Anderes Jahr: raus.
        lstb(3, year=2024, gross_amount=99999.0),
    ]

    summary = build_elster_summary(2025, docs)

    assert positions(summary, "anlage_n")["gross_amount"]["amount"] == 11000.0
    assert positions(summary, "vorsorgeaufwand")["insurance_other"]["amount"] == 150.0


def test_empty_year_has_empty_positions():
    summary = build_elster_summary(2019, [])

    for anlage in summary["anlagen"]:
        for position in anlage["positions"]:
            assert position["status"] == EMPTY
            assert position["amount"] == 0.0

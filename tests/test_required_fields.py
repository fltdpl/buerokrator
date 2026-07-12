"""Leere und leere Pflichtfelder im Formular-Schema."""

from src.core.document_types import EMPLOYMENT, INVOICE, PENSION, TAX
from src.services.form_schema import (
    empty_fields,
    form_fields,
    is_empty_value,
    missing_required_fields,
)


def test_null_ist_ein_wert_keine_luecke():
    # 0,00 EUR steht so im Dokument (z. B. Kirchensteuer) und ist erfasst.
    assert not is_empty_value(0.0)
    assert is_empty_value(None)
    assert is_empty_value("")
    assert is_empty_value("   ")


def test_vollstaendige_rechnung_hat_keine_luecken():
    data = {
        "issuer": "Amazon",
        "document_date": "11.03.2026",
        "invoice_number": "RE-123",
        "amount": 42.0,
    }

    assert missing_required_fields(INVOICE, data) == []
    assert empty_fields(INVOICE, data) == []


def test_leere_pflichtfelder_werden_gemeldet():
    data = {"invoice_number": "RE-123", "amount": None, "issuer": ""}

    missing = missing_required_fields(INVOICE, data)

    assert set(missing) == {"issuer", "document_date", "amount"}


def test_pflichtfelder_sind_teilmenge_der_leeren_felder():
    data = {"issuer": "Amazon"}

    missing = missing_required_fields(INVOICE, data)
    empty = empty_fields(INVOICE, data)

    assert set(missing) <= set(empty)
    # Die Rechnungsnummer ist leer, aber kein Pflichtfeld.
    assert "invoice_number" in empty
    assert "invoice_number" not in missing


def test_pflichtfelder_haengen_am_subtyp():
    data = {"tax_year": "2024"}

    # Ohne bekannten Subtyp bietet tax nur das Steuerjahr an.
    assert missing_required_fields(TAX, data) == []
    # Die Gehaltsabrechnung ist ein Arbeit-Subtyp; Steuerjahr ist vorhanden,
    # Arbeitgeber und Bruttolohn fehlen.
    assert missing_required_fields(EMPLOYMENT, data, subtype="gehaltsabrechnung") == [
        "employer",
        "gross_amount",
    ]


def test_jedes_schema_feld_traegt_das_required_flag():
    # Sonst würde ein neu ergänztes Feld still als "nicht Pflicht" gelten,
    # ohne dass jemand darüber entschieden hat.
    for document_type in (INVOICE, PENSION):
        for field in form_fields(document_type):
            assert "required" in field

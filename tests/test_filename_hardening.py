"""Dateinamen-Bau muss LLM-Ausgaben überleben, die vom Schema abweichen:
Zahlen statt Strings, None, Pfadseparatoren in Feldwerten (Review P1)."""

from src.organizer.filename_builder import (
    build_bank_filename,
    build_employment_filename,
    build_insurance_filename,
    build_invoice_filename,
    build_pension_filename,
)


def test_invoice_with_numeric_llm_values():
    # invoice_number als Zahl, amount als deutscher String -> kein Crash.
    filename = build_invoice_filename(
        {
            "document_date": "01.03.2024",
            "issuer": "ACME",
            "invoice_number": 12345,
            "amount": "1.234",
        },
        ".pdf",
    )

    # "1.234" ist 1234 EUR (Tausenderpunkt), nicht 1 EUR.
    assert filename == "2024-03-01_ACME_12345_1234EUR.pdf"


def test_invoice_with_none_values_uses_defaults():
    filename = build_invoice_filename(
        {"document_date": None, "issuer": None, "invoice_number": None},
        ".pdf",
    )

    assert filename == "unknown_date_unknown_issuer.pdf"


def test_insurance_with_numeric_policy_number():
    filename = build_insurance_filename(
        {
            "document_date": "01.01.2024",
            "issuer": "Debeka Lebensversicherungsverein a. G.",
            "insurance_type": "Haftpflicht",
            "policy_number": 987654,
        },
        ".pdf",
    )

    assert filename == "2024-01-01_Debeka_Haftpflicht_987654.pdf"


def test_pension_subtype_with_slash_is_sanitized():
    # Ein Modellwert mit "/" darf kein Pfadseparator werden.
    filename = build_pension_filename(
        {
            "document_date": "01.01.2024",
            "issuer": "Debeka",
            "document_subtype": "contract/../../etc",
            "policy_number": "P-1",
        },
        ".pdf",
    )

    assert "/" not in filename
    assert filename == "2024-01-01_Debeka_contract_.._.._etc_P-1.pdf"


def test_bank_issuer_with_slash_is_sanitized():
    filename = build_bank_filename(
        {
            "document_date": "01.01.2024",
            "issuer": "Bank/Depot AG",
            "document_subtype": "Kontoauszug",
        },
        ".pdf",
    )

    assert "/" not in filename


def test_employment_with_non_string_issuer():
    filename = build_employment_filename(
        {
            "document_subtype": "kuendigung",
            "issuer": 42,
            "document_date": "01.03.2024",
            "subject": None,
        },
        ".pdf",
    )

    assert filename == "2024-03-01_42_kuendigung.pdf"

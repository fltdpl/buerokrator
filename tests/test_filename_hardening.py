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


def test_insurance_with_numeric_policy_number(tmp_path):
    # Alias-Datei im (test-isolierten) App-Home: der lange Vereinsname wird
    # im Dateinamen auf den kanonischen Namen vereinheitlicht.
    (tmp_path / "aussteller_aliase.yaml").write_text(
        "Musterkasse:\n  - Musterkasse Lebensversicherungsverein a. G.\n",
        encoding="utf-8",
    )

    filename = build_insurance_filename(
        {
            "document_date": "01.01.2024",
            "issuer": "Musterkasse Lebensversicherungsverein a. G.",
            "insurance_type": "Haftpflicht",
            "policy_number": 987654,
        },
        ".pdf",
    )

    assert filename == "2024-01-01_Musterkasse_Haftpflicht_987654.pdf"


def test_pension_subtype_with_slash_is_sanitized():
    # Ein Modellwert mit "/" darf kein Pfadseparator werden.
    filename = build_pension_filename(
        {
            "document_date": "01.01.2024",
            "issuer": "Musterkasse",
            "document_subtype": "contract/../../etc",
            "policy_number": "P-1",
        },
        ".pdf",
    )

    assert "/" not in filename
    assert filename == "2024-01-01_Musterkasse_contract_.._.._etc_P-1.pdf"


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


# --------------------------------------------- Datums-/Jahresfelder (Review)
#
# `_clean_name` deckte nur issuer/subtype ab. document_date, tax_year, month
# und period_start/-end liefen ungefiltert in den Dateinamen — `normalize_date`
# gibt unparsbare Werte unverändert zurück.


def test_document_date_kann_nicht_aus_dem_archiv_ausbrechen():
    filename = build_invoice_filename(
        {"document_date": "../../../tmp/pwned", "issuer": "ACME"},
        ".pdf",
    )

    assert "/" not in filename
    assert not filename.startswith("..")


def test_tax_year_kann_nicht_aus_dem_archiv_ausbrechen():
    from src.organizer.filename_builder import build_tax_filename

    filename = build_tax_filename(
        {"tax_year": "../../../tmp/pwned", "issuer": "Finanzamt"},
        ".pdf",
    )

    assert "/" not in filename
    assert not filename.startswith("..")


def test_monat_kann_kein_unterverzeichnis_erzeugen():
    filename = build_employment_filename(
        {
            "document_subtype": "gehaltsabrechnung",
            "tax_year": 2024,
            "month": "../x",
            "employer": "Musterfirma",
        },
        ".pdf",
    )

    assert "/" not in filename


def test_datum_mit_schraegstrichen_erzeugt_keine_unterordner():
    # Häufigster Alltagsfall: das LLM liefert "01/03/2024". normalize_date
    # parst nur "%d.%m.%Y" und reichte den Rohwert durch -> der Import scheiterte
    # anschließend am fehlenden Elternverzeichnis.
    filename = build_invoice_filename(
        {
            "document_date": "01/03/2024",
            "issuer": "ACME",
            "invoice_number": "R1",
            "amount": 10,
        },
        ".pdf",
    )

    assert filename == "01_03_2024_ACME_R1_10EUR.pdf"


def test_windows_verbotene_zeichen_werden_ersetzt():
    # Windows-Paket ist erklärtes Ziel: < > : " | ? * und "\" sind dort
    # in Dateinamen unzulässig, "\" ist zusätzlich Pfadseparator.
    filename = build_invoice_filename(
        {
            "document_date": "01.03.2024",
            "issuer": r"..\..\windows",
            "invoice_number": 'R:1?"',
        },
        ".pdf",
    )

    assert not any(char in filename for char in '<>:"|?*\\/')


def test_reservierter_windows_name_wird_entschaerft():
    from src.organizer.filename_builder import build_legal_filename

    filename = build_legal_filename(
        {"document_date": "", "issuer": "", "subject": ""},
        ".pdf",
    )

    # Ein leerer Bau darf keinen leeren oder reservierten Namen liefern.
    assert filename not in ("", ".pdf")


def test_sehr_langer_name_bleibt_im_dateisystem_limit():
    # 255 Bytes ist die Grenze je Pfadkomponente (ext4, NTFS).
    filename = build_invoice_filename(
        {"document_date": "01.03.2024", "issuer": "A" * 400, "invoice_number": "R1"},
        ".pdf",
    )

    assert len(filename.encode("utf-8")) <= 255
    assert filename.endswith(".pdf")

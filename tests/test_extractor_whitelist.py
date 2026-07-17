import src.classifier.document_extractor as de


def test_extract_invoice_strips_unknown_fields(monkeypatch):
    def fake_run_extractor(prompt_file, text, max_input_chars=None):
        return {
            "issuer": "EnBW Energie Baden-Württemberg AG",
            "document_date": "05.05.2026",
            "invoice_number": "180 163 391 572",
            "amount": 167.0,
            "currency": "EUR",
            "account_number": "422174XXXXXX5419",
            "customer_number": "DE-NBW-C55512345-X",
            "delivery_country": "Deutschland",
        }

    monkeypatch.setattr(de, "run_extractor", fake_run_extractor)

    data = de.extract_invoice("irgendein Text")

    assert set(data.keys()) == {
        "issuer",
        "document_date",
        "invoice_number",
        "amount",
    }
    assert data["amount"] == 167.0


def test_extract_bank_strips_unknown_fields(monkeypatch):
    def fake_run_extractor(prompt_file, text, max_input_chars=None):
        return {
            "issuer": "Sparkasse",
            "document_date": "01.01.2020",
            "document_subtype": "Kontoauszug",
            "iban": "DE00...",
            "balance": 100.0,
        }

    monkeypatch.setattr(de, "run_extractor", fake_run_extractor)

    data = de.extract_bank("text")

    assert set(data.keys()) == {"issuer", "document_date", "document_subtype"}


def test_extract_tax_keeps_schema_and_normalizes(monkeypatch):
    def fake_run_extractor(prompt_file, text, max_input_chars=None):
        return {
            "employer": "ACME",
            "document_subtype": "lohnsteuerbescheinigung",
            "tax_year": "2024",
            "gross_amount": "45.000,00",
            "income_tax": "8.230,50",
            "steuer_id": "12345678901",  # nicht im Schema
        }

    monkeypatch.setattr(de, "run_extractor", fake_run_extractor)

    data = de.extract_tax("text")

    assert "steuer_id" not in data
    assert data["gross_amount"] == 45000.0
    assert data["income_tax"] == 8230.5


def test_extract_returns_empty_on_non_dict(monkeypatch):
    monkeypatch.setattr(
        de,
        "run_extractor",
        lambda prompt_file, text, max_input_chars=None: ["kein", "dict"],
    )

    assert de.extract_invoice("text") == {}


def test_extract_employment_keeps_sv_fields_of_lohnsteuerbescheinigung(monkeypatch):
    # SV-Beiträge (LStB Zeilen 22–27) für die Anlage Vorsorgeaufwand:
    # überstehen die Whitelist, deutsche Formate werden normalisiert,
    # versehentliche Minuszeichen entfernt. Alle Zahlen erfunden.
    def fake_run_extractor(prompt_file, text, max_input_chars=None):
        return {
            "document_subtype": "lohnsteuerbescheinigung",
            "employer": "Musterfirma GmbH",
            "tax_year": "2025",
            "gross_amount": "38.500,00",
            "pension_insurance_employer": "3.580,50",
            "pension_insurance_employee": -3580.5,
            "health_insurance": "2.810,25",
            "care_insurance": 655.75,
            "unemployment_insurance": "500,50",
            "sv_nummer": "99 999999 X 99",  # nicht im Schema
        }

    monkeypatch.setattr(de, "run_extractor", fake_run_extractor)

    data = de.extract_employment("text")

    assert "sv_nummer" not in data
    assert data["pension_insurance_employer"] == 3580.5
    assert data["pension_insurance_employee"] == 3580.5  # Magnitude
    assert data["health_insurance"] == 2810.25
    assert data["care_insurance"] == 655.75
    assert data["unemployment_insurance"] == 500.5


def test_extract_employment_strips_sv_fields_from_gehaltsabrechnung(monkeypatch):
    # Gehaltsabrechnungen tragen keine SV-Jahresfelder — die Whitelist
    # verwirft sie (Subtyp-Feldset).
    def fake_run_extractor(prompt_file, text, max_input_chars=None):
        return {
            "document_subtype": "gehaltsabrechnung",
            "employer": "Musterfirma GmbH",
            "tax_year": "2025",
            "gross_amount": 3100.0,
            "net_amount": 2050.0,
            "pension_insurance_employee": 288.3,
        }

    monkeypatch.setattr(de, "run_extractor", fake_run_extractor)

    data = de.extract_employment("text")

    assert "pension_insurance_employee" not in data
    assert data["net_amount"] == 2050.0

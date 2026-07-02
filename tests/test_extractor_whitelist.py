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

import src.classifier.document_extractor as de
from src.core.amount_utils import enforce_amount_signs


def test_enforce_amount_signs_magnitude_and_signed():
    data = {
        "capital_gains_tax": -30.0,
        "soli": -1.65,
        "income_tax": 8000.0,
        "settlement_amount": -740.74,  # bleibt negativ (Erstattung)
        "tax_year": "2024",  # kein Betrag -> unangetastet
    }

    result = enforce_amount_signs(data)

    assert result["capital_gains_tax"] == 30.0
    assert result["soli"] == 1.65
    assert result["income_tax"] == 8000.0
    assert result["settlement_amount"] == -740.74
    assert result["tax_year"] == "2024"


def test_extract_tax_forces_magnitude(monkeypatch):
    def fake_run_extractor(prompt_file, text, max_input_chars=None):
        return {
            "document_subtype": "einkommensbescheinigung",
            "issuer": "Finanzamt",
            "tax_year": "2024",
            "income_tax": "-3.000,00",
            "soli": "-165,00",
            "settlement_amount": "-740,74",
        }

    monkeypatch.setattr(de, "run_extractor", fake_run_extractor)

    data = de.extract_tax("text")

    assert data["income_tax"] == 3000.0
    assert data["soli"] == 165.0
    # Abrechnungsbetrag darf negativ bleiben (Erstattung).
    assert data["settlement_amount"] == -740.74

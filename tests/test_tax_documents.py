import src.classifier.document_extractor as document_extractor
from src.classifier.document_classifier import classify
from src.classifier.rule_classifier import match_rule
from src.organizer.filename_builder import build_tax_filename


def test_match_rule_recognizes_tax_documents():
    assert match_rule("Ausdruck der elektronischen Lohnsteuerbescheinigung") == "tax"
    assert match_rule("Ihre Gehaltsabrechnung März 2024") == "tax"
    assert match_rule("Entgeltabrechnung") == "tax"
    assert match_rule("Verdienstbescheinigung") == "tax"
    assert match_rule("Einkommensbescheinigung für Monat 03/2024") == "tax"


def test_match_rule_tax_beats_insurance_keyword():
    # Gehaltsabrechnung enthält oft "Sozialversicherung" - darf nicht als
    # insurance erkannt werden.
    text = "Gehaltsabrechnung mit Sozialversicherung und Rentenversicherung"
    assert match_rule(text) == "tax"


def test_match_rule_returns_none_without_match():
    assert match_rule("Ein beliebiger Text ohne Schlüsselwort") is None


def test_classify_uses_rule_precheck_without_llm():
    # Trifft eine Regel, wird das LLM nicht bemüht (kein Ollama nötig).
    result = classify("Ausdruck der elektronischen Lohnsteuerbescheinigung 2024")
    assert result["document_type"] == "tax"
    assert result["source"] == "rule"


def test_build_tax_filename_lohnsteuerbescheinigung_uses_year_month():
    data = {
        "document_subtype": "lohnsteuerbescheinigung",
        "employer": "ACME AG",
        "tax_year": "2024",
    }
    # Ohne konkreten Monat: Jahresende (12) als möglichst vollständiges Datum.
    assert (
        build_tax_filename(data, ".pdf")
        == "2024-12_ACME_AG_Lohnsteuerbescheinigung.pdf"
    )


def test_build_tax_filename_lohnsteuer_uses_month_when_present():
    data = {
        "document_subtype": "lohnsteuerbescheinigung",
        "employer": "ACME AG",
        "tax_year": "2024",
        "month": "3",
    }
    assert (
        build_tax_filename(data, ".pdf")
        == "2024-03_ACME_AG_Lohnsteuerbescheinigung.pdf"
    )


def test_build_tax_filename_einkommensbescheinigung_uses_year_month():
    data = {
        "document_subtype": "einkommensbescheinigung",
        "employer": "ACME AG",
        "tax_year": "2024",
        "month": "3",
    }
    assert (
        build_tax_filename(data, ".pdf")
        == "2024-03_ACME_AG_Einkommensbescheinigung.pdf"
    )


def test_build_tax_filename_defaults_to_lohnsteuer_without_subtype():
    data = {"employer": "ACME", "tax_year": "2024"}
    assert (
        build_tax_filename(data, ".pdf") == "2024-12_ACME_Lohnsteuerbescheinigung.pdf"
    )


def test_extract_tax_normalizes_amounts(monkeypatch):
    def fake_run_extractor(prompt_file, text, max_input_chars=None):
        return {
            "employer": "ACME",
            "document_subtype": "lohnsteuerbescheinigung",
            "tax_year": "2024",
            "month": "",
            "gross_amount": "45.000,00",
            "income_tax": "8.230,50",
            "soli": "0",
            "church_tax": "740,74 €",
            "net_amount": None,
        }

    monkeypatch.setattr(document_extractor, "run_extractor", fake_run_extractor)

    data = document_extractor.extract_tax("irgendein Text")

    assert data["gross_amount"] == 45000.0
    assert data["income_tax"] == 8230.5
    assert data["soli"] == 0.0
    assert data["church_tax"] == 740.74
    assert data["net_amount"] is None

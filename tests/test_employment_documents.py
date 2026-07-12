import src.classifier.document_extractor as document_extractor
from src.classifier.document_classifier import classify
from src.classifier.rule_classifier import match_rule
from src.organizer.filename_builder import build_employment_filename


def test_match_rule_recognizes_employment_documents():
    assert match_rule("Ausdruck der elektronischen Lohnsteuerbescheinigung") == "employment"
    assert match_rule("Ihre Gehaltsabrechnung März 2024") == "employment"
    assert match_rule("Entgeltabrechnung") == "employment"
    assert match_rule("Verdienstbescheinigung") == "employment"
    assert match_rule("Arbeitsvertrag zwischen Firma und Mitarbeiter") == "employment"


def test_match_rule_employment_beats_insurance_keyword():
    # Gehaltsabrechnung enthält oft "Sozialversicherung" - darf nicht als
    # insurance erkannt werden.
    text = "Gehaltsabrechnung mit Sozialversicherung und Rentenversicherung"
    assert match_rule(text) == "employment"


def test_classify_uses_rule_precheck_without_llm():
    # Trifft eine Regel, wird das LLM nicht bemüht (kein Ollama nötig).
    result = classify("Ausdruck der elektronischen Lohnsteuerbescheinigung 2024")
    assert result["document_type"] == "employment"
    assert result["source"] == "rule"


def test_build_employment_filename_lohnsteuerbescheinigung_uses_year_month():
    data = {
        "document_subtype": "lohnsteuerbescheinigung",
        "employer": "ACME AG",
        "tax_year": "2024",
    }
    # Ohne konkreten Monat: Jahresende (12) als möglichst vollständiges Datum.
    assert (
        build_employment_filename(data, ".pdf")
        == "2024-12_ACME_AG_Lohnsteuerbescheinigung.pdf"
    )


def test_build_employment_filename_lohnsteuer_uses_month_when_present():
    data = {
        "document_subtype": "lohnsteuerbescheinigung",
        "employer": "ACME AG",
        "tax_year": "2024",
        "month": "3",
    }
    assert (
        build_employment_filename(data, ".pdf")
        == "2024-03_ACME_AG_Lohnsteuerbescheinigung.pdf"
    )


def test_build_employment_filename_gehaltsabrechnung_uses_year_month():
    data = {
        "document_subtype": "gehaltsabrechnung",
        "employer": "ACME AG",
        "tax_year": "2024",
        "month": "3",
    }
    assert (
        build_employment_filename(data, ".pdf")
        == "2024-03_ACME_AG_Gehaltsabrechnung.pdf"
    )


def test_build_employment_filename_arbeitsvertrag_uses_date_issuer_subject():
    data = {
        "document_subtype": "arbeitsvertrag",
        "issuer": "ACME AG",
        "document_date": "01.03.2024",
        "subject": "Anstellung Vollzeit",
    }
    assert (
        build_employment_filename(data, ".pdf")
        == "2024-03-01_ACME_AG_Anstellung_Vollzeit.pdf"
    )


def test_extract_employment_lohnsteuer_normalizes_and_whitelists(monkeypatch):
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

    data = document_extractor.extract_employment("irgendein Text")

    assert data["gross_amount"] == 45000.0
    assert data["income_tax"] == 8230.5
    assert data["soli"] == 0.0
    assert data["church_tax"] == 740.74
    # net_amount gehört nicht zur Lohnsteuerbescheinigung -> weggefiltert.
    assert "net_amount" not in data


def test_extract_employment_contract_keeps_subject(monkeypatch):
    def fake_run_extractor(prompt_file, text, max_input_chars=None):
        return {
            "document_subtype": "arbeitsvertrag",
            "issuer": "ACME AG",
            "document_date": "01.03.2024",
            "subject": "Anstellung Vollzeit",
            "gross_amount": "45.000,00",  # gehört nicht zu diesem Subtyp
        }

    monkeypatch.setattr(document_extractor, "run_extractor", fake_run_extractor)

    data = document_extractor.extract_employment("text")

    assert data["issuer"] == "ACME AG"
    assert data["subject"] == "Anstellung Vollzeit"
    assert "gross_amount" not in data

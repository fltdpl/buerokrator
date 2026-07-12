import src.classifier.document_extractor as document_extractor
from src.classifier.rule_classifier import match_rule
from src.organizer.filename_builder import build_tax_filename


def test_match_rule_recognizes_finanzamt_documents():
    assert match_rule("Einkommensbescheinigung für Monat 03/2024") == "tax"
    assert match_rule("Einkommensteuerbescheid 2024") == "tax"


def test_match_rule_meldebescheinigung_is_tax():
    assert match_rule("Meldebescheinigung zur Sozialversicherung") == "tax"


def test_match_rule_returns_none_without_match():
    assert match_rule("Ein beliebiger Text ohne Schlüsselwort") is None


def test_build_tax_filename_einkommensbescheinigung_finanzamt():
    data = {
        "document_subtype": "einkommensbescheinigung",
        "issuer": "Finanzamt Karlsruhe",
        "tax_year": "2024",
        "settlement_amount": -740.74,
    }
    assert (
        build_tax_filename(data, ".pdf")
        == "2024-12_Finanzamt_Karlsruhe_Einkommensbescheinigung.pdf"
    )


def test_build_tax_filename_bescheinigung():
    data = {
        "document_subtype": "bescheinigung",
        "issuer": "AOK",
        "tax_year": "2024",
    }
    assert build_tax_filename(data, ".pdf") == "2024_AOK_Bescheinigung.pdf"


def test_build_tax_filename_defaults_to_bescheinigung_without_subtype():
    # Lohnsteuer/Gehalt sind nach employment gewandert; der tax-Default ist
    # jetzt die generische Bescheinigung.
    data = {"issuer": "AOK", "tax_year": "2024"}
    assert build_tax_filename(data, ".pdf") == "2024_AOK_Bescheinigung.pdf"


def test_extract_tax_finanzamt_keeps_only_subtype_fields(monkeypatch):
    def fake_run_extractor(prompt_file, text, max_input_chars=None):
        return {
            "document_subtype": "einkommensbescheinigung",
            "issuer": "Finanzamt Karlsruhe",
            "tax_year": "2024",
            "income_tax": "3.000,00",
            "soli": "0",
            "settlement_amount": "-740,74",
            "gross_amount": "45.000,00",  # gehört nicht zu diesem Subtyp
            "employer": "ACME",  # gehört nicht zu diesem Subtyp
        }

    monkeypatch.setattr(document_extractor, "run_extractor", fake_run_extractor)

    data = document_extractor.extract_tax("text")

    assert data["settlement_amount"] == -740.74
    assert data["income_tax"] == 3000.0
    assert data["issuer"] == "Finanzamt Karlsruhe"
    # Felder anderer Subtypen werden verworfen.
    assert "gross_amount" not in data
    assert "employer" not in data

import json
import sqlite3

from src.evaluation.comparator import (
    aggregate_results,
    compare_document,
    values_match,
)
from src.evaluation.ground_truth import load_ground_truth


def make_case(**overrides):
    case = {
        "name": "tax_beispiel",
        "file": "examples/tax/beispiel.pdf",
        "document_type": "tax",
        "fields": {
            "document_subtype": "lohnsteuerbescheinigung",
            "gross_amount": 54321.0,
            "employer": "Muster GmbH",
        },
        "verified": True,
    }
    case.update(overrides)
    return case


class TestValuesMatch:
    def test_amounts_within_tolerance(self):
        assert values_match(100.0, 100.005)
        assert not values_match(100.0, 100.02)

    def test_amount_as_string(self):
        assert values_match(1234.5, "1234,50")
        assert values_match("1234.5", 1234.5)

    def test_strings_normalized(self):
        assert values_match("Muster GmbH", "  muster   gmbh ")
        assert not values_match("Muster GmbH", "Andere AG")

    def test_none_handling(self):
        assert values_match(None, None)
        assert not values_match(None, "x")
        assert not values_match("x", None)

    def test_bool_not_treated_as_number(self):
        assert not values_match(1.0, True)

    def test_dates_match_across_formats(self):
        assert values_match("31.12.2022", "2022-12-31")
        assert values_match("05.05.2026", "05. Mai 2026")
        assert values_match("5.5.2026", "05.05.2026")
        assert not values_match("31.12.2022", "01.01.2023")
        assert not values_match("31.12.2022", "")

    def test_empty_expected_matches_empty_actual(self):
        assert values_match("", None)
        assert values_match(None, "")
        assert values_match("", "  ")
        assert not values_match("", "990001112223")

    def test_issuer_containment_counts_as_match(self):
        assert values_match("Debeka Bausparkasse", "Debeka Bausparkasse AG")
        assert values_match("Deutsche Wohnen Management GmbH", "Deutsche Wohnen")
        # Kurze Fragmente dürfen nicht per Teilstring matchen
        assert not values_match("AG", "Debeka Bausparkasse AG")
        assert not values_match("Bausparvertrag", "Steuerbescheinigung")

    def test_company_form_aliases(self):
        assert values_match(
            "Debeka Bausparkasse AG",
            "Debeka Bausparkasse Aktiengesellschaft",
        )


class TestCompareDocument:
    def test_all_correct(self):
        case = make_case()
        result = compare_document(
            case,
            "tax",
            {
                "document_subtype": "lohnsteuerbescheinigung",
                "gross_amount": 54321.0,
                "employer": "Muster GmbH",
            },
        )
        assert result["type_correct"]
        assert result["fields_correct"] == 3
        assert result["fields_total"] == 3
        assert result["spurious"] == []

    def test_wrong_type_and_missing_field(self):
        case = make_case()
        result = compare_document(
            case,
            "invoice",
            {"gross_amount": 99.0},
        )
        assert not result["type_correct"]
        assert result["fields"]["gross_amount"]["status"] == "wrong"
        assert result["fields"]["employer"]["status"] == "missing"
        assert result["fields_correct"] == 0

    def test_spurious_fields_reported_not_counted(self):
        case = make_case(fields={"employer": "Muster GmbH"})
        result = compare_document(
            case,
            "tax",
            {"employer": "Muster GmbH", "erfundenes_feld": "x"},
        )
        assert result["fields_correct"] == 1
        assert result["spurious"] == ["erfundenes_feld"]

    def test_expected_none_and_absent_field_is_correct(self):
        case = make_case(fields={"soli": None, "employer": "Muster GmbH"})
        result = compare_document(case, "tax", {"employer": "Muster GmbH"})
        assert result["fields"]["soli"]["status"] == "correct"
        assert result["fields_correct"] == 2

    def test_empty_extraction(self):
        result = compare_document(make_case(), "tax", None)
        assert result["fields_correct"] == 0
        assert all(f["status"] == "missing" for f in result["fields"].values())


class TestAggregateResults:
    def test_aggregation(self):
        case_ok = make_case()
        case_bad = make_case(name="tax_bad")
        results = [
            compare_document(
                case_ok,
                "tax",
                {
                    "document_subtype": "lohnsteuerbescheinigung",
                    "gross_amount": 54321.0,
                    "employer": "Muster GmbH",
                },
            ),
            compare_document(case_bad, "invoice", {}),
        ]
        summary = aggregate_results(results)
        assert summary["documents"] == 2
        assert summary["classification_accuracy"] == 0.5
        assert summary["fields_correct"] == 3
        assert summary["fields_total"] == 6
        assert summary["field_accuracy"] == 0.5
        assert summary["by_type"]["tax"]["docs"] == 2

    def test_empty(self):
        summary = aggregate_results([])
        assert summary["classification_accuracy"] is None
        assert summary["field_accuracy"] is None


def setup_test_db(tmp_path, monkeypatch, rows):
    """Legt eine Test-DB mit documents-Tabelle an und richtet die Config darauf aus."""
    db_path = tmp_path / "database" / "buerokrator.db"
    db_path.parent.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        f"database:\n  path: {db_path}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                archive_path TEXT,
                document_type TEXT,
                extracted_data TEXT,
                created_at TEXT,
                verified INTEGER DEFAULT 0,
                document_text TEXT,
                notes TEXT,
                tax_year TEXT
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO documents (filename, document_type, extracted_data, verified, document_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )


class TestGroundTruthFromDatabase:
    def test_loads_only_verified_documents_with_text(self, tmp_path, monkeypatch):
        setup_test_db(
            tmp_path,
            monkeypatch,
            [
                (
                    "a.pdf",
                    "tax",
                    # document_date ist für tax nicht gewhitelistet und muss
                    # aus den Sollwerten herausgefiltert werden.
                    json.dumps({"gross_amount": 1000.0, "document_date": "01.01.2024"}),
                    1,
                    "Text A",
                ),
                ("b.pdf", "invoice", json.dumps({"amount": 5.0}), 0, "Text B"),
                ("c.pdf", "pension", json.dumps({"amount": 7.0}), 1, None),
                ("d.pdf", "pension", json.dumps({"amount": 7.0}), 1, ""),
            ],
        )

        cases = load_ground_truth()
        assert len(cases) == 1
        case = cases[0]
        assert case["name"] == "#1 a.pdf"
        assert case["document_type"] == "tax"
        assert case["fields"] == {"gross_amount": 1000.0}
        assert case["document_text"] == "Text A"
        assert case["verified"] is True

    def test_type_filter_and_limit(self, tmp_path, monkeypatch):
        setup_test_db(
            tmp_path,
            monkeypatch,
            [
                ("a.pdf", "tax", "{}", 1, "T"),
                ("b.pdf", "pension", "{}", 1, "T"),
                ("c.pdf", "pension", "{}", 1, "T"),
            ],
        )

        pension = load_ground_truth(document_type="pension")
        assert [c["file"] for c in pension] == ["b.pdf", "c.pdf"]

        limited = load_ground_truth(limit=2)
        assert len(limited) == 2

    def test_broken_extracted_data_yields_empty_fields(self, tmp_path, monkeypatch):
        setup_test_db(
            tmp_path,
            monkeypatch,
            [
                ("a.pdf", "tax", "kein json", 1, "T"),
                ("b.pdf", "tax", None, 1, "T"),
                ("c.pdf", "tax", json.dumps(["liste"]), 1, "T"),
            ],
        )

        cases = load_ground_truth()
        assert len(cases) == 3
        assert all(case["fields"] == {} for case in cases)

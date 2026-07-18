"""Golden-Master-Abgleich der ELSTER-Zuordnung. Alle Zahlen erfunden."""

import yaml

from src.tax.elster_check import build_template, compare_year, format_report
from tests.test_elster_mapping import lstb, make_row


def test_matching_expectation_is_accepted():
    docs = [lstb(1, gross_amount=38500.0, income_tax=5120.0)]
    expected = {
        "anlage_n": {"gross_amount": 38500.0, "income_tax": 5120.0},
    }

    report = compare_year(2025, expected, docs)

    assert report["ok"] is True
    assert all(entry["ok"] for entry in report["checked"])
    assert "ABGENOMMEN" in format_report(report)


def test_difference_fails_and_shows_derivation():
    docs = [lstb(1, gross_amount=38500.0)]
    expected = {"anlage_n": {"gross_amount": 40000.0}}

    report = compare_year(2025, expected, docs)

    assert report["ok"] is False
    text = format_report(report)
    assert "DIFF" in text
    # Herleitung: der Beleg steht im Report.
    assert "dok_1.pdf" in text
    assert "NICHT abgenommen" in text


def test_typo_in_expectation_is_an_error_not_a_pass():
    docs = [lstb(1, gross_amount=38500.0)]
    expected = {"anlage_n": {"gross_amout": 38500.0}}  # Tippfehler

    report = compare_year(2025, expected, docs)

    assert report["ok"] is False
    assert any("gross_amout" in error for error in report["errors"])


def test_positions_without_expectation_are_reported_as_unchecked():
    docs = [
        lstb(1, gross_amount=38500.0, income_tax=5120.0),
    ]
    expected = {"anlage_n": {"gross_amount": 38500.0}}

    report = compare_year(2025, expected, docs)

    # income_tax hat einen App-Befund, aber keinen Erwartungswert.
    unchecked_keys = {entry["key"] for entry in report["unchecked"]}
    assert "anlage_n.income_tax" in unchecked_keys
    # Leere Positionen (z. B. KAP ohne Belege) werden nicht gelistet.
    assert not any(key.startswith("kap.") for key in unchecked_keys)


def test_empty_expectation_is_not_accepted():
    report = compare_year(2025, {}, [lstb(1, gross_amount=38500.0)])

    assert report["checked"] == []
    assert report["ok"] is False


def test_tolerance_is_cent_exact():
    docs = [lstb(1, gross_amount=100.004)]

    assert compare_year(2025, {"anlage_n": {"gross_amount": 100.0}}, docs)["ok"]
    assert not compare_year(2025, {"anlage_n": {"gross_amount": 100.02}}, docs)["ok"]


def test_unclear_insurance_appears_in_diff_report():
    docs = [
        make_row(1, "insurance", 2025, {"amount": 300.0}),
    ]
    expected = {"vorsorgeaufwand": {"insurance_other": 300.0}}

    report = compare_year(2025, expected, docs)

    # Unklare Art zählt nicht in die Summe → Differenz, Beleg gelistet.
    assert report["ok"] is False
    assert "Unklare Art" in format_report(report)


def test_template_is_valid_yaml_without_active_values():
    template = build_template(2025, [lstb(1, gross_amount=38500.0)])

    parsed = yaml.safe_load(template)

    # Alle Anlagen da, aber keine Werte einkommentiert (kein
    # Bestätigungsfehler durch vorbefüllte App-Werte).
    assert set(parsed) == {"anlage_n", "vorsorgeaufwand", "kap"}
    assert all(value is None for value in parsed.values())
    assert "gross_amount" in template  # als Kommentar-Vorlage enthalten

    # Eine frische (leere) Vorlage erzeugt keine Fehler, nur "nicht ok".
    report = compare_year(2025, parsed, [lstb(1, gross_amount=38500.0)])
    assert report["errors"] == []
    assert report["ok"] is False


def test_whole_euro_expectation_tolerates_taxfix_rounding():
    # Taxfix rundet auf ganze Euro: 38500 gegen App-Wert 38500.47 ist ok.
    docs = [lstb(1, gross_amount=38500.47)]

    report = compare_year(2025, {"anlage_n": {"gross_amount": 38500}}, docs)

    assert report["ok"] is True
    assert report["checked"][0]["rounded"] is True
    assert "±1 €" in format_report(report)

    # Mehr als 1 € Abstand bleibt eine Differenz …
    assert not compare_year(2025, {"anlage_n": {"gross_amount": 38502}}, docs)["ok"]
    # … und Cent-Erwartungen bleiben cent-genau.
    assert not compare_year(
        2025, {"anlage_n": {"gross_amount": 38500.40}}, docs
    )["ok"]

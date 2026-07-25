"""Aussteller-Aliase aus der App-Home-Datei. Alle Namen erfunden.

Die conftest-Fixture leitet aliases_path auf tmp_path um — Tests schreiben
ihre Alias-Datei direkt dorthin.
"""

from src.classifier.document_extractor import extract_document
from src.organizer.issuer_normalizer import (
    apply_issuer_aliases,
    ensure_aliases_file,
    load_aliases,
    normalize_issuer,
)


def write_aliases(tmp_path, content):
    (tmp_path / "aussteller_aliase.yaml").write_text(content, encoding="utf-8")


ALIASES = """\
Musterkasse:
  - Musterkasse Lebensversicherungsverein a. G.
  - "Musterkasse Versichern und Bausparen*"
Musterbank AG:
  - MB Musterbank Aktiengesellschaft
"""


def test_exact_and_prefix_match(tmp_path):
    write_aliases(tmp_path, ALIASES)

    assert (
        normalize_issuer("Musterkasse Lebensversicherungsverein a. G.")
        == "Musterkasse"
    )
    assert (
        normalize_issuer("Musterkasse Versichern und Bausparen AG")
        == "Musterkasse"
    )
    assert normalize_issuer("MB Musterbank Aktiengesellschaft") == "Musterbank AG"
    # Unbekannte und kanonische Namen bleiben unverändert.
    assert normalize_issuer("Musterkasse") == "Musterkasse"
    assert normalize_issuer("Fremdfirma GmbH") == "Fremdfirma GmbH"


def test_missing_file_changes_nothing():
    assert load_aliases() == ({}, ())
    assert normalize_issuer("Musterkasse Lebensversicherungsverein a. G.") == (
        "Musterkasse Lebensversicherungsverein a. G."
    )


def test_broken_yaml_is_a_warning_not_a_crash(tmp_path):
    write_aliases(tmp_path, "kein: [gültiges: yaml")

    assert load_aliases() == ({}, ())
    assert normalize_issuer("Musterbank AG") == "Musterbank AG"


def test_non_mapping_content_is_rejected(tmp_path):
    write_aliases(tmp_path, "- nur\n- eine\n- liste\n")

    assert load_aliases() == ({}, ())


def test_edit_takes_effect_without_restart(tmp_path):
    write_aliases(tmp_path, "Musterbank AG:\n  - MB Musterbank\n")
    assert normalize_issuer("MB Musterbank") == "Musterbank AG"

    # Datei ändern: der mtime/size-Cache muss neu laden.
    write_aliases(tmp_path, "Musterbank eG:\n  - MB Musterbank\n")
    assert normalize_issuer("MB Musterbank") == "Musterbank eG"


def test_apply_issuer_aliases_covers_all_name_fields(tmp_path):
    write_aliases(
        tmp_path,
        "Musterfirma GmbH:\n"
        "  - Musterfirma Gesellschaft mit beschränkter Haftung\n",
    )
    alias = "Musterfirma Gesellschaft mit beschränkter Haftung"

    data = apply_issuer_aliases(
        {
            "issuer": alias,
            "employer": alias,
            "insurer": alias,
            "subject": alias,  # kein Namensfeld — bleibt unverändert
            "amount": 12.5,
        }
    )

    assert data["issuer"] == "Musterfirma GmbH"
    assert data["employer"] == "Musterfirma GmbH"
    assert data["insurer"] == "Musterfirma GmbH"
    assert data["subject"] == alias
    assert data["amount"] == 12.5


def test_extract_document_applies_aliases(tmp_path, monkeypatch):
    # Der zentrale Hook: Import und „Erneut prüfen" speichern direkt den
    # kanonischen Namen.
    write_aliases(tmp_path, "Musterbank AG:\n  - MB Musterbank\n")

    import src.classifier.document_extractor as extractor_module

    monkeypatch.setattr(
        extractor_module,
        "extract_invoice",
        lambda text: {"issuer": "MB Musterbank", "amount": 10.0},
    )

    data = extract_document("invoice", "Beispieltext")

    assert data["issuer"] == "Musterbank AG"


def test_ensure_aliases_file_creates_template_once(tmp_path):
    path = ensure_aliases_file()

    assert path == tmp_path / "aussteller_aliase.yaml"
    assert "Musterkasse" in path.read_text(encoding="utf-8")
    # Nur Kommentare: die Vorlage definiert noch keine Zuordnung.
    assert load_aliases() == ({}, ())

    path.write_text("Musterbank AG:\n  - MB Musterbank\n", encoding="utf-8")
    ensure_aliases_file()  # vorhandene Datei bleibt unangetastet

    assert normalize_issuer("MB Musterbank") == "Musterbank AG"

from pathlib import Path

from src.organizer.filename_builder import rename_document


def write_config(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                "  archive: ./archive",
                "database:",
                "  path: ./database/buerokrator.db",
                "archive:",
                "  category_mapping:",
                "    tax: Steuern",
                "    insurance: Versicherungen",
            ]
        ),
        encoding="utf-8",
    )


def test_rename_moves_to_year_from_data_on_reclassification(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    old_folder = tmp_path / "archive" / "1985" / "Versicherungen"
    old_folder.mkdir(parents=True)
    source = old_folder / "1985-03-14_Alt.pdf"
    source.write_text("inhalt")

    extracted = {
        "document_subtype": "gehaltsabrechnung",
        "employer": "ACME",
        "tax_year": "2009",
        "month": "11",
    }

    new_path = rename_document(
        "archive/1985/Versicherungen/1985-03-14_Alt.pdf",
        "tax",
        extracted,
    )

    # Zielordner nach Dokumentjahr (2009), nicht nach altem Pfad (1985).
    assert new_path == Path("archive") / "2009" / "Steuern" / (
        "2009-11_ACME_Gehaltsabrechnung.pdf"
    )
    assert (tmp_path / new_path).exists()
    assert not source.exists()


def test_rename_keeps_year_from_document_date(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    old_folder = tmp_path / "archive" / "1985" / "Versicherungen"
    old_folder.mkdir(parents=True)
    source = old_folder / "1985-03-14_Alt.pdf"
    source.write_text("inhalt")

    extracted = {
        "issuer": "HUK",
        "insurance_type": "Haftpflicht",
        "policy_number": "P1",
        "document_date": "14.03.1985",
    }

    new_path = rename_document(
        "archive/1985/Versicherungen/1985-03-14_Alt.pdf",
        "insurance",
        extracted,
    )

    assert new_path.parts[:2] == ("archive", "1985")
    assert (tmp_path / new_path).exists()

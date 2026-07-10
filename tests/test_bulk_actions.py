"""Bulk-Aktionen der Dokumentenliste: löschen, umklassifizieren."""

import src.database.database as database
from src.database.document_repository import insert_document
from src.database.list_documents import get_document
from src.database.set_document_verified import set_document_verified
from src.services.document_service import move_documents_to_trash, reclassify_documents


def _setup_project(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                f"  inbox: {tmp_path / 'inbox'}",
                f"  archive: {tmp_path / 'archive'}",
                "database:",
                f"  path: {tmp_path / 'database' / 'test.db'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(database, "_schema_ready", False)


def _document(tmp_path, name, document_type="invoice", with_file=True):
    archive = tmp_path / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    path = archive / name

    if with_file:
        path.write_text("pdf", encoding="utf-8")

    return insert_document(
        filename=name,
        archive_path=str(path),
        document_type=document_type,
        extracted_data={},
    )


def test_mehrere_dokumente_in_den_papierkorb(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    first = _document(tmp_path, "a.pdf")
    second = _document(tmp_path, "b.pdf")
    trash = tmp_path / "trash"

    assert move_documents_to_trash([first, second], trash_dir=trash) == 2
    assert get_document(first) is None
    assert get_document(second) is None
    assert {path.name for path in trash.iterdir()} == {"a.pdf", "b.pdf"}


def test_fehlende_archivdatei_verhindert_das_loeschen_nicht(tmp_path, monkeypatch):
    # Der DB-Eintrag ist gelöscht, auch wenn das PDF schon weg war.
    _setup_project(tmp_path, monkeypatch)
    document_id = _document(tmp_path, "verschwunden.pdf", with_file=False)

    assert move_documents_to_trash([document_id], trash_dir=tmp_path / "trash") == 1
    assert get_document(document_id) is None


def test_unbekannte_ids_werden_uebersprungen(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    document_id = _document(tmp_path, "a.pdf")

    assert move_documents_to_trash([document_id, 999], trash_dir=tmp_path / "trash") == 1


def test_umklassifizieren_setzt_typ_und_prueffstatus_zurueck(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    document_id = _document(tmp_path, "a.pdf", document_type="invoice")
    set_document_verified(document_id, 1)

    assert reclassify_documents([document_id], "housing") == 1

    row = get_document(document_id)
    assert row["document_type"] == "housing"
    # Nach einem Typwechsel gelten andere Felder: erneut prüfen.
    assert row["verified"] == 0


def test_umklassifizieren_laesst_die_datei_wo_sie_ist(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    document_id = _document(tmp_path, "a.pdf")

    reclassify_documents([document_id], "housing")

    assert (tmp_path / "archive" / "a.pdf").exists()

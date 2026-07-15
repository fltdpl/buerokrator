"""Tests für „Erneut prüfen": Klassifikation + Extraktion auf dem
gespeicherten Text wiederholen, Freigabe widerrufen, tax_relevant-Reset.
LLM-Aufrufe sind gemockt."""

import json

import src.services.document_service as service
from src.database.database import open_connection
from src.database.document_repository import insert_document
from src.database.init_database import init_database
from src.database.list_documents import get_document
from src.database.update_document import update_document


def write_config(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                "  inbox: ./inbox",
                "  archive: ./archive",
                "  exports: ./exports",
                "database:",
                "  path: ./database/buerokrator.db",
            ]
        ),
        encoding="utf-8",
    )


def insert_verified_document(document_text="Rechnungstext"):
    document_id = insert_document(
        filename="2020-01-01_alt.pdf",
        archive_path="archive/2020/Kategorie/2020-01-01_alt.pdf",
        document_type="pension",
        extracted_data={"issuer": "Alt AG", "tax_year": "2020"},
        document_text=document_text,
    )

    # Prüf-Workflow nachstellen: korrigierte Werte, verified = 1, Override.
    update_document(
        document_id=document_id,
        filename="2020-01-01_alt.pdf",
        archive_path="archive/2020/Kategorie/2020-01-01_alt.pdf",
        document_type="pension",
        extracted_data={"issuer": "Alt AG (korrigiert)", "tax_year": "2020"},
        tax_relevant=1,
    )

    return document_id


def test_reanalyze_overwrites_and_unverifies(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()
    document_id = insert_verified_document()

    seen = {}

    def fake_classify(text):
        seen["classify_text"] = text
        return {"document_type": "invoice", "source": "llm"}

    def fake_extract(document_type, text):
        seen["extract_type"] = document_type
        return {"issuer": "Neu GmbH", "document_date": "01.03.2021"}

    monkeypatch.setattr(service, "classify", fake_classify)
    monkeypatch.setattr(service, "extract_document", fake_extract)

    result = service.reanalyze_document(document_id)

    assert result == {"ok": True, "error": None, "document_type": "invoice"}
    assert seen["classify_text"] == "Rechnungstext"
    assert seen["extract_type"] == "invoice"

    row = get_document(document_id)
    assert row["document_type"] == "invoice"
    assert json.loads(row["extracted_data"]) == {
        "issuer": "Neu GmbH",
        "document_date": "01.03.2021",
    }
    assert row["verified"] == 0
    assert row["tax_relevant"] is None

    # tax_year (nicht Teil von get_document) muss dem neuen Datum folgen.
    with open_connection() as conn:
        tax_year = conn.execute(
            "SELECT tax_year FROM documents WHERE id = ?", (document_id,)
        ).fetchone()["tax_year"]

    assert tax_year == "2021"
    # Unangetastet: Text und Datei.
    assert row["document_text"] == "Rechnungstext"
    assert row["archive_path"] == "archive/2020/Kategorie/2020-01-01_alt.pdf"


def test_reanalyze_error_keeps_document_unchanged(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()
    document_id = insert_verified_document()

    def boom(text):
        raise ConnectionError("Ollama nicht erreichbar")

    monkeypatch.setattr(service, "classify", boom)

    result = service.reanalyze_document(document_id)

    assert result["ok"] is False
    assert "Ollama" in result["error"]

    row = get_document(document_id)
    assert row["verified"] == 1
    assert row["tax_relevant"] == 1
    assert json.loads(row["extracted_data"])["issuer"] == "Alt AG (korrigiert)"


def test_reanalyze_without_text_refuses(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()
    document_id = insert_verified_document(document_text="")

    result = service.reanalyze_document(document_id)

    assert result["ok"] is False
    assert "Dokumenttext" in result["error"]
    assert get_document(document_id)["verified"] == 1


def test_reanalyze_missing_document(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()

    result = service.reanalyze_document(4711)

    assert result["ok"] is False
    assert "nicht gefunden" in result["error"]

"""Dubletten-Erkennung beim Import (Inhalts-Hash)."""

import src.database.database as database
import src.processor.document_processor as processor
from src.core.file_hash import file_hash
from src.database.document_repository import insert_document
from src.database.find_duplicate import find_document_by_hash


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
                "archive:",
                "  category_mapping:",
                "    invoice: Rechnungen",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(database, "_schema_ready", False)


def test_hash_haengt_am_inhalt_nicht_am_namen(tmp_path):
    (tmp_path / "rechnung.pdf").write_bytes(b"inhalt")
    (tmp_path / "rechnung (1).pdf").write_bytes(b"inhalt")
    (tmp_path / "andere.pdf").write_bytes(b"anderer inhalt")

    assert file_hash(tmp_path / "rechnung.pdf") == file_hash(
        tmp_path / "rechnung (1).pdf"
    )
    assert file_hash(tmp_path / "rechnung.pdf") != file_hash(tmp_path / "andere.pdf")


def test_find_document_by_hash(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    document_id = insert_document(
        filename="2024-01-01_Amazon.pdf",
        archive_path="archive/2024/Rechnungen/2024-01-01_Amazon.pdf",
        document_type="invoice",
        extracted_data={},
        content_hash="abc123",
    )

    assert find_document_by_hash("abc123") == (document_id, "2024-01-01_Amazon.pdf")
    assert find_document_by_hash("unbekannt") is None


def test_altbestand_ohne_hash_matcht_nicht(tmp_path, monkeypatch):
    # Dokumente aus der Zeit vor der Dubletten-Erkennung haben content_hash
    # NULL. Ein leerer Hash darf sie nicht alle als Dublette treffen.
    _setup_project(tmp_path, monkeypatch)

    insert_document(
        filename="alt.pdf",
        archive_path="archive/alt.pdf",
        document_type="invoice",
        extracted_data={},
    )

    assert find_document_by_hash(None) is None
    assert find_document_by_hash("") is None


def test_dublette_wird_ohne_ocr_und_llm_in_den_papierkorb_verschoben(
    tmp_path, monkeypatch
):
    _setup_project(tmp_path, monkeypatch)

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    original = inbox / "rechnung.pdf"
    original.write_bytes(b"inhalt")

    document_id = insert_document(
        filename="2024-01-01_Amazon.pdf",
        archive_path="archive/2024/Rechnungen/2024-01-01_Amazon.pdf",
        document_type="invoice",
        extracted_data={},
        content_hash=file_hash(original),
    )

    # Wenn die Pipeline hier anläuft, ist die Erkennung zu spät.
    def fail(*args, **kwargs):
        raise AssertionError("Dublette darf nicht analysiert werden")

    monkeypatch.setattr(processor, "analyze_document", fail)

    result = processor.process(str(original))

    assert result["duplicate_of"] == document_id
    assert result["duplicate_filename"] == "2024-01-01_Amazon.pdf"
    assert not original.exists()
    assert (tmp_path / "trash" / "rechnung.pdf").read_bytes() == b"inhalt"


def test_neues_dokument_wird_mit_hash_gespeichert(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    source = inbox / "neu.pdf"
    source.write_bytes(b"frischer inhalt")

    monkeypatch.setattr(
        processor,
        "analyze_document",
        lambda path: {
            "classification": {"document_type": "invoice"},
            "extracted_data": {"issuer": "Amazon", "document_date": "01.01.2024"},
            "document_text": "Rechnung",
        },
    )

    result = processor.process(str(source))

    assert "duplicate_of" not in result
    assert find_document_by_hash(file_hash(result["archive_path"])) == (
        result["document_id"],
        result["filename"],
    )

import importlib
import json
from pathlib import Path

from src.core.document_types import ARCHIVE_CATEGORY_LABELS


def write_test_config(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    archive_mapping = [
        f"    {document_type}: {label}"
        for document_type, label in ARCHIVE_CATEGORY_LABELS.items()
    ]
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                "  inbox: ./inbox",
                "  archive: ./archive",
                "  exports: ./exports",
                "database:",
                "  path: ./database/buerokrator.db",
                "ocr:",
                "  language: deu+eng",
                "  tesseract:",
                "    windows: ''",
                "    linux: ''",
                "classifier:",
                "  mode: llm",
                "  model: test-model",
                "  max_input_chars: 3000",
                "  temperature: 0.0",
                "archive:",
                "  category_mapping:",
                *archive_mapping,
            ]
        ),
        encoding="utf-8",
    )


def load_pipeline_modules():
    import src.database.database as database
    import src.database.init_database as init_database
    import src.database.list_documents as list_documents
    import src.database.search as search
    import src.organizer.category_mapper as category_mapper
    import src.processor.document_processor as document_processor

    for module in (
        database,
        init_database,
        list_documents,
        search,
        category_mapper,
        document_processor,
    ):
        importlib.reload(module)

    return init_database, list_documents, search, document_processor


def test_process_archives_invoice_and_stores_document_metadata(
    tmp_path,
    monkeypatch,
):
    # Dummy-PDF statt echter Beispieldatei: OCR/Klassifikation/Extraktion
    # sind gemockt, die Datei wird nur gehasht und verschoben. So hängt der
    # Test nicht an privaten (unversionierten) Dateien in examples/.
    original_pdf_bytes = b"%PDF-1.4\n% Dummy fuer den Pipeline-Test\n%%EOF\n"

    write_test_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    source_file = inbox / "Rechnung_Zahnarzt_OCR.pdf"
    source_file.write_bytes(original_pdf_bytes)

    init_database, list_documents, search, document_processor = load_pipeline_modules()
    init_database.init_database()

    document_text = "Amazon Rechnung RE-123 vom 11.03.2026 ueber 42,50 EUR"
    classification = {
        "document_type": "invoice",
    }
    extracted_data = {
        "issuer": "Amazon",
        "document_date": "11.03.2026",
        "invoice_number": "RE/123",
        "amount": 42.5,
    }

    monkeypatch.setattr(
        document_processor,
        "extract_text",
        lambda file_path: document_text,
    )
    monkeypatch.setattr(
        document_processor,
        "classify",
        lambda text: classification,
    )
    monkeypatch.setattr(
        document_processor,
        "extract_document",
        lambda document_type, text: extracted_data,
    )

    document_processor.process(str(source_file))

    assert not source_file.exists()

    documents = list_documents.list_documents()
    assert len(documents) == 1

    row = documents[0]
    assert row["filename"] == "2026-03-11_Amazon_RE-123_42EUR.pdf"
    # Archivpfad ist jetzt App-Home-verankert (absolut), nicht cwd-relativ.
    assert row["archive_path"] == str(
        tmp_path
        / "archive"
        / "2026"
        / "Rechnungen"
        / "2026-03-11_Amazon_RE-123_42EUR.pdf"
    )
    assert row["document_type"] == "invoice"
    assert json.loads(row["extracted_data"]) == extracted_data
    assert row["verified"] == 0
    assert row["document_text"] == document_text

    archived_file = Path(row["archive_path"])
    assert archived_file.exists()
    assert archived_file.read_bytes() == original_pdf_bytes

    search_results = search.search_documents("Amazon")
    assert len(search_results) == 1
    assert search_results[0]["filename"] == row["filename"]

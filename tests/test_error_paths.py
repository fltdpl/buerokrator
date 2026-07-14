"""Fehlerpfade der Pipeline (Review P5): OCR-Ausfall und kaputte LLM-Antworten
dürfen die Verarbeitung nicht crashen — sie enden kontrolliert (None bzw. {})."""

import src.classifier.document_extractor as document_extractor
import src.processor.document_processor as document_processor


def test_process_returns_none_when_ocr_fails(tmp_path, monkeypatch):
    # Echte Datei, damit wait_for_file/file_hash normal durchlaufen.
    pdf = tmp_path / "kaputt.pdf"
    pdf.write_bytes(b"%PDF-1.5 fake")

    # Keine Dublette; OCR wirft (z. B. Tesseract fehlt / Datei unlesbar).
    monkeypatch.setattr(
        document_processor, "find_document_by_hash", lambda content_hash: None
    )

    def broken_ocr(file_path):
        raise RuntimeError("OCR fehlgeschlagen")

    monkeypatch.setattr(document_processor, "extract_text", broken_ocr)

    result = document_processor.process(str(pdf))

    # Kontrolliert gescheitert: None (Frontend zählt die Datei als
    # fehlgeschlagen), Datei bleibt in der Inbox liegen.
    assert result is None
    assert pdf.exists()


def test_extract_returns_empty_dict_when_llm_json_broken(monkeypatch):
    # Beide Versuche (1 Retry) liefern kein parsebares JSON.
    def broken_extractor(prompt_file, text, max_input_chars=None):
        raise ValueError("kein JSON")

    monkeypatch.setattr(document_extractor, "run_extractor", broken_extractor)

    assert document_extractor.extract_invoice("irgendein Text") == {}
    assert document_extractor.extract_employment("irgendein Text") == {}


def test_extract_returns_empty_dict_for_non_dict_response(monkeypatch):
    # LLM liefert gültiges JSON, aber kein Objekt (z. B. eine Liste).
    monkeypatch.setattr(
        document_extractor,
        "run_extractor",
        lambda prompt_file, text, max_input_chars=None: ["kein", "dict"],
    )

    assert document_extractor.extract_invoice("Text") == {}

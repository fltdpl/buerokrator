"""Ollama ist optional: Import degradiert sauber, Schutzchecks greifen."""

import pytest


# ---------------------------------------------------------------- classify


def test_classify_without_ollama_falls_back_to_unknown(monkeypatch):
    import src.classifier.document_classifier as dc

    # Kein Regel-Treffer, LLM nicht erreichbar.
    monkeypatch.setattr(dc, "match_rule", lambda text: None)
    monkeypatch.setattr(
        dc,
        "load_config",
        lambda: {
            "classifier": {
                "model": "gemma3:4b",
                "max_input_chars": 1000,
                "temperature": 0.0,
            }
        },
    )

    def boom(**kwargs):
        raise ConnectionError("connection refused")

    monkeypatch.setattr(dc, "chat", boom)

    result = dc.classify("völlig unklarer Text")

    assert result == {"document_type": "unknown", "source": "none"}


def test_classify_rule_hit_needs_no_ollama(monkeypatch):
    import src.classifier.document_classifier as dc

    monkeypatch.setattr(dc, "match_rule", lambda text: "employment")

    def boom(**kwargs):
        raise AssertionError("LLM darf bei Regel-Treffer nicht aufgerufen werden")

    monkeypatch.setattr(dc, "chat", boom)

    result = dc.classify("Gehaltsabrechnung ...")

    assert result == {"document_type": "employment", "source": "rule"}


# ------------------------------------------------------- reanalyze-Schutz


def test_reanalyze_refuses_without_ollama(monkeypatch):
    import src.services.document_service as ds

    monkeypatch.setattr(ds, "get_document", lambda document_id: {
        "id": 1,
        "document_text": "genug Text",
    })
    monkeypatch.setattr(ds, "is_ollama_available", lambda: False)

    def boom(*args, **kwargs):
        raise AssertionError("ohne Ollama darf nicht analysiert werden")

    monkeypatch.setattr(ds, "classify", boom)
    monkeypatch.setattr(ds, "replace_document_analysis", boom)

    result = ds.reanalyze_document(1)

    assert result["ok"] is False
    assert "Ollama" in result["error"]


# ------------------------------------------------------ Evaluation-Schutz


def test_run_evaluation_aborts_without_ollama(monkeypatch):
    import src.classifier.ollama_availability as availability
    import src.evaluation.runner as runner

    monkeypatch.setattr(availability, "is_ollama_available", lambda: False)

    with pytest.raises(SystemExit, match="Ollama"):
        runner.run_evaluation(limit=1)


# ------------------------------------------------------ Dependency-Status


def test_ollama_status_is_optional(monkeypatch):
    import src.services.dependency_service as dep

    def boom():
        raise ConnectionError("refused")

    monkeypatch.setattr(dep, "_installed_model_names", boom)

    status = dep.check_ollama()

    assert status["ok"] is False
    assert status["required"] is False


def test_tesseract_status_is_required(monkeypatch):
    import src.services.dependency_service as dep

    status = dep.check_tesseract(
        {"ocr": {"tesseract": {"linux": "", "windows": ""}}}
    )

    assert status["required"] is True

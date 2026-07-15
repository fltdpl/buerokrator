import src.services.dependency_service as dep

BASE_CONFIG = {
    "classifier": {"model": "gemma3:4b"},
    "ocr": {
        "tesseract": {"linux": "", "windows": ""},
    },
}


def test_check_ollama_ok(monkeypatch):
    monkeypatch.setattr(dep, "_installed_model_names", lambda: ["gemma3:4b", "llama3"])

    status = dep.check_ollama()

    assert status["ok"] is True
    assert "2 Modell" in status["detail"]


def test_check_ollama_unreachable(monkeypatch):
    def boom():
        raise ConnectionError("refused")

    monkeypatch.setattr(dep, "_installed_model_names", boom)

    status = dep.check_ollama()

    assert status["ok"] is False


def test_check_model_installed(monkeypatch):
    monkeypatch.setattr(dep, "_installed_model_names", lambda: ["gemma3:4b"])

    status = dep.check_model(BASE_CONFIG)

    assert status["ok"] is True


def test_check_model_missing_suggests_pull(monkeypatch):
    monkeypatch.setattr(dep, "_installed_model_names", lambda: ["llama3"])

    status = dep.check_model(BASE_CONFIG)

    assert status["ok"] is False
    assert "ollama pull gemma3:4b" in status["detail"]


def test_check_pdf_renderer_ok():
    status = dep.check_pdf_renderer()

    assert status["ok"] is True
    assert "PDFium" in status["detail"]


def test_collect_returns_all_four(monkeypatch):
    monkeypatch.setattr(dep, "_installed_model_names", lambda: ["gemma3:4b"])

    statuses = dep.collect_dependency_status(BASE_CONFIG)

    assert [s["name"].split("„")[0].strip() for s in statuses][:1] == ["Ollama"]
    assert len(statuses) == 4
    assert all({"name", "ok", "detail"} <= set(s) for s in statuses)

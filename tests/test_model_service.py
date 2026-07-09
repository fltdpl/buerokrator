"""Installierte Ollama-Modelle für die Einstellungen."""

import src.services.model_service as model_service
from src.services.model_service import FALLBACK_MODELS, list_installed_models


def test_liest_installierte_modelle(monkeypatch):
    monkeypatch.setattr(
        model_service.ollama,
        "list",
        lambda: {"models": [{"model": "qwen3:1.7b"}, {"model": "gemma3:4b"}]},
    )

    assert list_installed_models() == ["gemma3:4b", "qwen3:1.7b"]


def test_kennt_auch_das_alte_feld_name(monkeypatch):
    # Ältere ollama-Versionen liefern "name" statt "model".
    monkeypatch.setattr(
        model_service.ollama, "list", lambda: {"models": [{"name": "llama3"}]}
    )

    assert list_installed_models() == ["llama3"]


def test_konfiguriertes_modell_bleibt_waehlbar(monkeypatch):
    # Sonst würde die Auswahl den gespeicherten Wert still verwerfen.
    monkeypatch.setattr(
        model_service.ollama, "list", lambda: {"models": [{"model": "gemma3:4b"}]}
    )

    options = list_installed_models(current_model="exotisch:70b")

    assert "exotisch:70b" in options
    assert "gemma3:4b" in options


def test_fallback_wenn_ollama_nicht_laeuft(monkeypatch):
    def boom():
        raise ConnectionError("Ollama antwortet nicht")

    monkeypatch.setattr(model_service.ollama, "list", boom)

    assert list_installed_models() == sorted(FALLBACK_MODELS)


def test_fallback_bei_leerer_liste(monkeypatch):
    monkeypatch.setattr(model_service.ollama, "list", lambda: {"models": []})

    assert list_installed_models() == sorted(FALLBACK_MODELS)

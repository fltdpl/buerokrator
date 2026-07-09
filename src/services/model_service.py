"""Installierte Ollama-Modelle abfragen (für die Einstellungen)."""

import ollama

from src.core.logger import logger

# Fallback, wenn Ollama nicht läuft: lieber eine bekannte Auswahl anbieten
# als ein leeres Feld, mit dem sich die Einstellungen nicht speichern lassen.
FALLBACK_MODELS = ["gemma3:4b", "qwen3:1.7b", "llama3"]


def _model_name(entry):
    """Ollama liefert je nach Version `model` oder `name`."""
    if isinstance(entry, dict):
        return entry.get("model") or entry.get("name")

    return getattr(entry, "model", None) or getattr(entry, "name", None)


def list_installed_models(current_model=None):
    """Namen der installierten Modelle, alphabetisch.

    `current_model` ist immer enthalten, auch wenn es (noch) nicht installiert
    ist — sonst würde die Auswahl den konfigurierten Wert still verwerfen.
    """
    try:
        response = ollama.list()
        models = response.get("models") if isinstance(response, dict) else response.models
        names = [name for entry in models if (name := _model_name(entry))]

    except Exception as error:
        logger.warning(f"Ollama-Modelle nicht abrufbar: {error}")
        names = list(FALLBACK_MODELS)

    if not names:
        names = list(FALLBACK_MODELS)

    if current_model and current_model not in names:
        names.append(current_model)

    return sorted(names)

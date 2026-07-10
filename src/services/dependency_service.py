"""Prüft, ob die externen Abhängigkeiten (Ollama, Modell, Tesseract, Poppler)
verfügbar sind — für die Statusanzeige in den Einstellungen.

Framework-neutral: jede Prüfung liefert ein dict {name, ok, detail}. Fehler
werden abgefangen und als `ok=False` mit Klartext-Detail gemeldet, statt die
Seite abstürzen zu lassen.
"""

import shutil
from pathlib import Path

from src.core.config import get_platform, load_config


def _status(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": detail}


def _installed_model_names():
    import ollama

    response = ollama.list()
    models = response.get("models") if isinstance(response, dict) else response.models
    names = []

    for entry in models:
        if isinstance(entry, dict):
            name = entry.get("model") or entry.get("name")

        else:
            name = getattr(entry, "model", None) or getattr(entry, "name", None)

        if name:
            names.append(name)

    return names


def check_ollama():
    try:
        names = _installed_model_names()

    except Exception as error:
        return _status(
            "Ollama", False, f"nicht erreichbar ({error}). Läuft der Dienst?"
        )

    return _status("Ollama", True, f"erreichbar, {len(names)} Modell(e) installiert")


def check_model(config):
    model = config["classifier"]["model"]

    try:
        names = _installed_model_names()

    except Exception:
        return _status(
            f"Modell „{model}“", False, "Ollama nicht erreichbar — Modell unklar"
        )

    if model in names:
        return _status(f"Modell „{model}“", True, "installiert")

    return _status(
        f"Modell „{model}“",
        False,
        f"nicht installiert — mit „ollama pull {model}“ nachladen",
    )


def check_tesseract(config):
    import pytesseract

    tesseract_path = config["ocr"]["tesseract"].get(get_platform())
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    try:
        version = pytesseract.get_tesseract_version()
        languages = set(pytesseract.get_languages())

    except Exception as error:
        return _status(
            "Tesseract OCR", False, f"nicht gefunden ({error})"
        )

    required = {"deu", "eng"}
    missing = required - languages
    if missing:
        return _status(
            "Tesseract OCR",
            False,
            f"v{version}, aber Sprachpaket(e) fehlen: {', '.join(sorted(missing))}",
        )

    return _status("Tesseract OCR", True, f"v{version}, Sprachen deu+eng vorhanden")


def check_poppler(config):
    poppler_path = config["ocr"]["poppler"].get(get_platform())

    if poppler_path:
        found = (Path(poppler_path) / "pdftoppm").exists() or (
            Path(poppler_path) / "pdftoppm.exe"
        ).exists()
        detail_path = poppler_path

    else:
        found = shutil.which("pdftoppm") is not None
        detail_path = "PATH"

    if found:
        return _status("Poppler", True, f"pdftoppm gefunden ({detail_path})")

    return _status(
        "Poppler",
        False,
        "pdftoppm nicht gefunden — für OCR gescannter PDFs nötig",
    )


def collect_dependency_status(config=None):
    """Statusliste aller externen Abhängigkeiten (für die Einstellungen)."""
    config = config or load_config()

    return [
        check_ollama(),
        check_model(config),
        check_tesseract(config),
        check_poppler(config),
    ]

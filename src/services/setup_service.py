"""First-Run-Assistent: framework-freie Logik für die Einrichtungsseite.

Entscheidet, ob eine Instanz frisch ist (Assistent zeigen), reichert den
Systemstatus aus dependency_service um Linux-Installationshinweise an und
merkt sich den Abschluss über eine Marker-Datei im App-Home.

Marker statt Config-Flag: die Config wird beim First-Run aus der Vorlage
kopiert — ein Flag in der Vorlage würde frische Installationen als
„eingerichtet" markieren.
"""

from pathlib import Path

from src.core.app_home import get_app_home
from src.core.config import load_config
from src.services.dependency_service import collect_dependency_status

_MARKER_NAME = ".setup_done"

# Hinweise pro Abhängigkeit (Schlüssel = Präfix des Statusnamens).
# Linux zuerst (Packaging-Entscheidung 15.07.2026); Windows folgt später.
_LINUX_HINTS = (
    ("Ollama", "curl -fsSL https://ollama.com/install.sh | sh"),
    ("Tesseract", "sudo apt install tesseract-ocr tesseract-ocr-deu"),
    (
        "PDF-Renderer",
        "pip install pypdfium2 (Teil der Python-Installation — fehlt nur"
        " bei defekter Umgebung)",
    ),
)


def setup_marker_path() -> Path:
    return get_app_home() / _MARKER_NAME


def needs_setup(config=None) -> bool:
    """Assistent nur für frische Instanzen: kein Marker UND noch keine DB.

    Die DB-Prüfung fängt Bestandsinstallationen ab, die es vor Einführung
    des Markers schon gab — wer bereits Dokumente hat, braucht keinen
    First-Run.
    """
    if setup_marker_path().exists():
        return False

    config = config or load_config()

    return not Path(config["database"]["path"]).exists()


def complete_setup() -> None:
    path = setup_marker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Einrichtung abgeschlossen.\n", encoding="utf-8")


def _hint_for(status_name: str, model: str) -> str:
    if status_name.startswith("Modell"):
        return f"ollama pull {model}"

    for prefix, hint in _LINUX_HINTS:
        if status_name.startswith(prefix):
            return hint

    return ""


def setup_checks(config=None) -> list:
    """Systemstatus + Installationshinweis je fehlender Abhängigkeit."""
    config = config or load_config()
    model = config["classifier"]["model"]
    checks = []

    for status in collect_dependency_status(config):
        checks.append({**status, "hint": _hint_for(status["name"], model)})

    return checks


def all_checks_ok(checks) -> bool:
    return all(check["ok"] for check in checks)

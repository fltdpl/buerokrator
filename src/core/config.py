import copy
import platform
import shutil
from pathlib import Path

import yaml

from src.core.app_home import get_app_home, resolve_path

# Config-Schlüssel mit Pfadwerten: werden beim Laden gegen das App-Home
# absolutiert (eine zentrale Stelle statt vieler Konsumenten) und beim
# Speichern wieder relativiert, wenn sie innerhalb des App-Home liegen —
# so bleibt die YAML-Datei portabel/diff-freundlich.
_PATH_KEYS = (
    ("paths", "inbox"),
    ("paths", "archive"),
    ("paths", "exports"),
    ("database", "path"),
    ("backup", "target"),
)

# Mitgelieferte Standard-Config (Repo bzw. PyInstaller-Datenverzeichnis) —
# Vorlage für den First-Run einer installierten Instanz. Bewusst keine
# zweite Kopie der Defaults im Code (der Konsistenztest zu den
# Dokumenttypen prüft genau diese Datei).
_TEMPLATE = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"


def config_path() -> Path:
    return get_app_home() / "config" / "settings.yaml"


def _ensure_config_exists(path: Path) -> None:
    """First-Run: Standard-Config aus der mitgelieferten Vorlage anlegen."""
    if path.exists():
        return

    if not _TEMPLATE.exists() or path == _TEMPLATE:
        raise FileNotFoundError(
            f"Keine Konfiguration gefunden ({path}) und keine Vorlage "
            f"verfügbar ({_TEMPLATE})."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_TEMPLATE, path)


def load_config() -> dict:
    path = config_path()
    _ensure_config_exists(path)

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for section, key in _PATH_KEYS:
        value = (config.get(section) or {}).get(key)

        if value:
            config[section][key] = str(resolve_path(value))

    return config


def save_config(config: dict) -> None:
    # Kopie: der Aufrufer soll sein (absolutiertes) dict weiterverwenden können.
    config = copy.deepcopy(config)
    home = get_app_home()

    for section, key in _PATH_KEYS:
        value = (config.get(section) or {}).get(key)

        if not value:
            continue

        value = Path(value)

        if value.is_absolute():
            try:
                config[section][key] = f"./{value.relative_to(home)}"

            except ValueError:
                # Außerhalb des App-Home (bewusst gewählter Ort): absolut lassen.
                pass

    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            config,
            f,
            allow_unicode=True,
            sort_keys=False,
        )


def get_platform() -> str:
    system = platform.system()
    if system == "Windows":
        return "windows"

    if system == "Linux":
        return "linux"

    raise RuntimeError(f"Nicht unterstütztes System: {system}")

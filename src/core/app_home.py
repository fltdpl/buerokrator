"""Datenverzeichnis der App — Entkopplung vom Arbeitsverzeichnis.

Bisher erwartete die App, aus dem Projektroot zu laufen (Config, Logs,
Archiv, Papierkorb relativ zur cwd). Eine installierte App hat kein
Projektverzeichnis; alle Pfade hängen deshalb jetzt an get_app_home().

Auflösung, in dieser Reihenfolge:
1. Umgebungsvariable BUEROKRATOR_HOME — explizit gewinnt (auch der
   Test-Override für Nicht-cwd-Szenarien).
2. Das aktuelle Arbeitsverzeichnis, wenn dort config/settings.yaml liegt
   (Entwickler-/Repo-Modus): exakt das bisherige Verhalten, darauf baut
   auch die Testsuite (chdir nach tmp_path + eigene Config).
3. Das plattformübliche Benutzer-Datenverzeichnis (installierte App):
   Linux $XDG_DATA_HOME/buerokrator bzw. ~/.local/share/buerokrator,
   Windows %APPDATA%/buerokrator.

Bewusst ohne platformdirs-Abhängigkeit: die App unterstützt nur Linux und
Windows (siehe config.get_platform), die zwei Zweige sind trivial.

Wichtig: get_app_home() wird bei jedem Aufruf neu ausgewertet (kein
Modul-Cache) — der cwd-Modus muss einem chdir der Tests folgen.
"""

import os
from pathlib import Path

APP_NAME = "buerokrator"


def _user_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(
            Path.home() / "AppData" / "Roaming"
        )
        return Path(base) / APP_NAME

    base = os.environ.get("XDG_DATA_HOME") or str(
        Path.home() / ".local" / "share"
    )
    return Path(base) / APP_NAME


def get_app_home() -> Path:
    env = os.environ.get("BUEROKRATOR_HOME")

    if env:
        return Path(env)

    if (Path.cwd() / "config" / "settings.yaml").exists():
        return Path.cwd()

    return _user_data_dir()


def resolve_path(value: "str | Path") -> Path:
    """Relative Pfade gegen das App-Home auflösen; absolute bleiben."""
    path = Path(value)

    if path.is_absolute():
        return path

    return get_app_home() / path

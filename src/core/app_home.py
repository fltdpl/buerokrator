"""Datenverzeichnisse der App — Entkopplung vom Arbeitsverzeichnis.

Bisher erwartete die App, aus dem Projektroot zu laufen (Config, Logs,
Archiv, Papierkorb relativ zur cwd). Eine installierte App hat kein
Projektverzeichnis; alle Pfade hängen deshalb an diesen Funktionen.

Es gibt **zwei** Wurzeln (siehe ADR 015):

- `get_base_home()` — die Installation: Einstellungen, Log, Profilliste,
  Setup-Marker, UI-Speicher. Für alle Personen dieselbe.
- `get_app_home()` — der Datenbestand des **aktiven Profils**: Datenbank,
  Archiv, Inbox, Papierkorb, Backups, Aussteller-Aliase.

Solange keine `profiles.yaml` in der Basis liegt, liefern beide dasselbe
Verzeichnis — eine Installation ohne Profile verhält sich exakt wie vor
Einführung dieser Ebene. Das ist die Verträglichkeitszusage, an der die
gesamte bestehende Testsuite und der Entwicklermodus hängen.

Auflösung der Basis, in dieser Reihenfolge:
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

Wichtig: die Basis wird bei jedem Aufruf neu ausgewertet (kein Modul-Cache)
— der cwd-Modus muss einem chdir der Tests folgen. Zwischengespeichert wird
nur der **Inhalt** von `profiles.yaml`, und zwar gegen Zeitstempel und Größe
geprüft: get_app_home() läuft bei jeder Pfadauflösung, eine YAML-Datei bei
jedem Aufruf zu parsen wäre im Stapelimport nicht vertretbar.
"""

import os
import re
from pathlib import Path

import yaml

APP_NAME = "buerokrator"

# Profilebene — optional, liegt über der Basis.
PROFILES_FILE = "profiles.yaml"
PROFILES_DIR = "profiles"

# Die Kennung wird zu einem Pfadsegment. Dieselbe Strenge wie beim
# Dateinamensbau: nichts, was aus dem Profilverzeichnis hinausführt.
_PROFILE_ID = re.compile(r"\A[A-Za-z0-9_-]+\Z")

# {Basis: ((mtime_ns, size), Kennung)} — siehe Modul-Docstring.
_ACTIVE_CACHE: dict[str, tuple[tuple[int, int], str]] = {}


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


def get_base_home() -> Path:
    """Wurzel der Installation — für alle Profile dieselbe."""
    env = os.environ.get("BUEROKRATOR_HOME")

    if env:
        return Path(env)

    if (Path.cwd() / "config" / "settings.yaml").exists():
        return Path.cwd()

    return _user_data_dir()


def _read_active_profile(base: Path) -> "str | None":
    """Kennung des aktiven Profils, oder None wenn es keine Profile gibt.

    Eine FEHLENDE Datei heißt „keine Profile" — das ist der Normalfall einer
    Einzelnutzer-Installation. Eine VORHANDENE, aber unbrauchbare Datei ist
    dagegen ein harter Fehler: nach der Profil-Migration liegt in der Basis
    kein Bestand mehr, ein stiller Rückfall dorthin würde eine leere
    Installation vortäuschen und neue Importe am Bestand vorbeischreiben.
    """
    path = base / PROFILES_FILE

    try:
        info = path.stat()

    except OSError:
        return None

    stamp = (info.st_mtime_ns, info.st_size)
    key = str(base)
    cached = _ACTIVE_CACHE.get(key)

    if cached is not None and cached[0] == stamp:
        return cached[1]

    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))

    except (OSError, yaml.YAMLError) as error:
        raise RuntimeError(f"{path} ist nicht lesbar: {error}") from error

    active = (content or {}).get("active") if isinstance(content, dict) else None

    if not isinstance(active, str) or not _PROFILE_ID.match(active):
        raise RuntimeError(
            f"{path} enthält keine gültige Profilkennung unter 'active' "
            f"(erlaubt sind Buchstaben, Ziffern, - und _)."
        )

    _ACTIVE_CACHE[key] = (stamp, active)

    return active


def reset_profile_cache() -> None:
    """Nach dem Umschalten und in Tests aufrufen.

    Der Zeitstempelvergleich fängt Änderungen von außen; beim Umschalten aus
    der App heraus wird trotzdem ausdrücklich verworfen, weil manche
    Dateisysteme die Zeit nur sekundengenau führen.
    """
    _ACTIVE_CACHE.clear()


def get_app_home() -> Path:
    """Datenverzeichnis des aktiven Profils (ohne Profile: die Basis)."""
    base = get_base_home()
    active = _read_active_profile(base)

    if active is None:
        return base

    return base / PROFILES_DIR / active


def resolve_path(value: "str | Path") -> Path:
    """Relative Pfade gegen das App-Home auflösen; absolute bleiben."""
    path = Path(value)

    if path.is_absolute():
        return path

    return get_app_home() / path

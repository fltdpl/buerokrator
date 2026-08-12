"""Datenverzeichnisse der App — Entkopplung vom Arbeitsverzeichnis.

Bisher erwartete die App, aus dem Projektroot zu laufen (Config, Logs,
Archiv, Papierkorb relativ zur cwd). Eine installierte App hat kein
Projektverzeichnis; alle Pfade hängen deshalb an diesen Funktionen.

Es gibt **zwei** Wurzeln (siehe ADR 015):

- `get_base_home()` — die Installation: Einstellungen, Log, Profilliste,
  Setup-Marker, UI-Speicher. Für alle Personen dieselbe.
- `get_app_home()` — der Datenbestand des **aktiven Profils**: Datenbank,
  Archiv, Inbox, Papierkorb, Backups, Aussteller-Aliase.

**Profile sind die einzige Struktur**, auch bei einer einzigen Person: die
Daten liegen immer unter `<basis>/profiles/<kennung>/`. Fehlt die
`profiles.yaml`, gilt `DEFAULT_PROFILE` — eine frische Installation braucht
die Datei also gar nicht, sie entsteht erst mit der zweiten Person oder einem
vergebenen Namen. Damit gibt es nur einen Verzeichnisaufbau statt zweier.

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

# Profilebene unter der Basis. Die Datei ist optional: ohne sie gilt
# DEFAULT_PROFILE, eine Einzelperson braucht also keine Verwaltung.
PROFILES_FILE = "profiles.yaml"
PROFILES_DIR = "profiles"
DEFAULT_PROFILE = "1"

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


def _read_active_profile(base: Path) -> str:
    """Kennung des aktiven Profils.

    Eine FEHLENDE Datei heißt `DEFAULT_PROFILE` — der Normalfall einer
    Installation mit einer Person, die nichts umbenannt hat. Eine VORHANDENE,
    aber unbrauchbare Datei ist dagegen ein harter Fehler: ein stiller
    Rückfall auf das Standardprofil würde einen fremden oder leeren Bestand
    öffnen und neue Importe am eigentlichen Bestand vorbeischreiben.
    """
    path = base / PROFILES_FILE

    try:
        info = path.stat()

    except OSError:
        return DEFAULT_PROFILE

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
    """Datenverzeichnis des aktiven Profils."""
    base = get_base_home()

    return base / PROFILES_DIR / _read_active_profile(base)


def resolve_path(value: "str | Path") -> Path:
    """Relative Pfade gegen das App-Home auflösen; absolute bleiben."""
    path = Path(value)

    if path.is_absolute():
        return path

    return get_app_home() / path


def resolve_archive_path(value) -> "Path | None":
    """`archive_path` einer Dokumentzeile auflösen — leer bleibt leer.

    Ältere Importe haben relative Pfade hinterlassen. Sie sind gegen das
    App-Home gemeint, lösten roh ausgewertet aber gegen das
    Arbeitsverzeichnis auf: die Existenzprüfung war damit zufällig, je
    nachdem, wo der Prozess gerade stand.

    Der Leerwert braucht die eigene Behandlung: `resolve_path("")` ergäbe das
    App-Home selbst — ein Verzeichnis, das existiert, sodass `exists()`
    fälschlich eine vorhandene Datei meldete.
    """
    if not value:
        return None

    return resolve_path(value)

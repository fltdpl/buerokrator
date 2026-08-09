"""Profile: mehrere Personen an einer Installation (ADR 015).

Framework-frei und testbar. Die Auflösung der Pfade liegt in
`core/app_home`; hier steht die Verwaltung.

**Profile sind die einzige Struktur**, auch bei einer einzigen Person: die
Daten liegen immer unter `<basis>/profiles/<kennung>/`. `profiles.yaml`
entsteht erst, wenn es etwas zu verwalten gibt — eine zweite Person oder
einen vergebenen Namen. Wer die App frisch installiert, sieht davon nichts.

Den einmaligen Umzug eines gewachsenen Bestands aus der alten, profillosen
Struktur macht `services/profile_port.py` — angeboten in der App und als
Werkzeug `tools/port_to_profiles.py`.
"""

from pathlib import Path

import yaml

from src.core.app_home import (
    DEFAULT_PROFILE,
    PROFILES_DIR,
    PROFILES_FILE,
    get_base_home,
    reset_profile_cache,
)
from src.core.logger import logger
from src.database.database import reset_schema_state
from src.services import background_jobs

# Deckel für die Anzahl gleichzeitig geführter Profile. Technisch bräuchte es
# ihn nicht — er markiert die Fläche: ein Haushalt, keine Mandantenfähigkeit.
# Er gilt für die ANZAHL, nicht für die Kennung: wer anlegt und entfernt,
# bekommt höhere Kennungen, aber nie eine Sperre durch sie.
MAX_PROFILE = 5


def _profiles_file() -> Path:
    return get_base_home() / PROFILES_FILE


def _profiles_root() -> Path:
    return get_base_home() / PROFILES_DIR


def _read_profiles() -> dict:
    """Verwaltungsstand; ohne Datei gilt das Standardprofil allein."""
    datei = _profiles_file()

    if not datei.exists():
        return {"active": DEFAULT_PROFILE, "profiles": [DEFAULT_PROFILE]}

    inhalt = yaml.safe_load(datei.read_text(encoding="utf-8"))

    if not isinstance(inhalt, dict):
        raise RuntimeError(f"{datei} ist unbrauchbar.")

    return {
        "active": inhalt.get("active"),
        "profiles": list(inhalt.get("profiles") or []),
    }


def _schreibe_profiles_datei(aktiv: str, profile: list) -> None:
    _profiles_file().write_text(
        yaml.safe_dump({"active": aktiv, "profiles": list(profile)}),
        encoding="utf-8",
    )


def profile_name(profile_id: str) -> str:
    """Anzeigename aus der Profildatei; Rückfall auf eine Vorbelegung."""
    pfad = _profiles_root() / profile_id / "profile.yaml"

    try:
        inhalt = yaml.safe_load(pfad.read_text(encoding="utf-8"))

    except (OSError, yaml.YAMLError):
        return default_profile_name(profile_id)

    name = (inhalt or {}).get("name") if isinstance(inhalt, dict) else None

    return (
        name if isinstance(name, str) and name.strip()
        else default_profile_name(profile_id)
    )


def default_profile_name(profile_id: str) -> str:
    return f"Benutzer {profile_id}"


def list_profiles() -> list:
    """Alle Profile in Anzeigereihenfolge: [{"id", "name", "active"}].

    Enthält immer mindestens einen Eintrag — es gibt keine Installation
    ohne Profil.
    """
    daten = _read_profiles()

    return [
        {
            "id": profile_id,
            "name": profile_name(profile_id),
            "active": profile_id == daten["active"],
        }
        for profile_id in daten["profiles"]
    ]


def active_profile() -> str:
    return _read_profiles()["active"]


def profile_exists(profile_id: str) -> bool:
    return (_profiles_root() / profile_id).is_dir()


def missing_profiles() -> list:
    """Gelistete Profile, deren Verzeichnis fehlt (verschoben, gelöscht).

    Das Standardprofil einer frischen Installation zählt nicht dazu: sein
    Verzeichnis entsteht erst beim ersten Schreibzugriff.
    """
    if not _profiles_file().exists():
        return []

    return [
        profile_id
        for profile_id in _read_profiles()["profiles"]
        if not profile_exists(profile_id)
    ]


def ensure_active_profile() -> "str | None":
    """Beim Start: fällt auf ein vorhandenes Profil zurück, wenn nötig.

    Fehlt das Verzeichnis des aktiven Profils (verschoben, gelöscht, ein
    externer Datenträger nicht eingehängt), würde die App es stillschweigend
    neu anlegen und wie eine leere Installation aussehen. Gibt die Meldung
    zurück, damit der Aufrufer sie zeigen kann — oder None, wenn alles passt.

    Eine frische Installation ohne `profiles.yaml` ist davon ausgenommen:
    dort ist das fehlende Verzeichnis der Normalzustand.

    Bewusst ohne Job-Sperre: das läuft beim Start, bevor etwas laufen kann.
    """
    if not _profiles_file().exists():
        return None

    daten = _read_profiles()

    if profile_exists(daten["active"]):
        return None

    ersatz = next((p for p in daten["profiles"] if profile_exists(p)), None)

    if ersatz is None:
        raise RuntimeError(
            "Kein einziges Profilverzeichnis gefunden. Liegt der Datenordner "
            "noch am erwarteten Ort?"
        )

    meldung = (
        f"Das zuletzt genutzte Profil {profile_name(daten['active'])!r} "
        f"wurde nicht gefunden. Geöffnet ist stattdessen "
        f"{profile_name(ersatz)!r}."
    )

    _schreibe_profiles_datei(ersatz, daten["profiles"])
    reset_profile_cache()
    reset_schema_state()
    logger.warning(meldung)

    return meldung


def _lege_profil_an(profile_id: str, name: str) -> Path:
    verzeichnis = _profiles_root() / profile_id
    verzeichnis.mkdir(parents=True, exist_ok=True)
    (verzeichnis / "profile.yaml").write_text(
        yaml.safe_dump({"name": name}, allow_unicode=True),
        encoding="utf-8",
    )

    return verzeichnis


def create_profile(name=None) -> str:
    """Legt ein weiteres Profil an und gibt seine Kennung zurück.

    Beim ersten Aufruf entsteht dabei auch `profiles.yaml`: bis dahin kam
    die Installation ohne Verwaltung aus.
    """
    daten = _read_profiles()

    if len(daten["profiles"]) >= MAX_PROFILE:
        raise RuntimeError(
            f"Mehr als {MAX_PROFILE} Personen sind nicht vorgesehen. Diese "
            "Ablage ist für einen Haushalt gedacht; wer eine Person nicht "
            "mehr braucht, nimmt sie aus der Liste."
        )

    # Erste Verwaltung: die bisher nur gedachten Profile werden real. Ohne
    # das fehlte dem Standardprofil sein Verzeichnis, und es gälte ab sofort
    # als „nicht gefunden" — der Start würde auf die neue Person umschalten.
    if not _profiles_file().exists():
        for vorhanden in daten["profiles"]:
            _lege_profil_an(vorhanden, profile_name(vorhanden))

    # Auch belegte VERZEICHNISSE zählen, nicht nur gelistete Profile.
    # `remove_profile` nimmt nur aus der Liste und lässt den Ordner liegen —
    # eine wiederverwendete Kennung würde der neuen Person den Bestand der
    # entfernten unterschieben.
    ziffern = [int(p) for p in daten["profiles"] if p.isdigit()]
    ziffern += [
        int(ordner.name)
        for ordner in _profiles_root().glob("*")
        if ordner.is_dir() and ordner.name.isdigit()
    ]
    neu = str(max(ziffern, default=0) + 1)

    _lege_profil_an(neu, name or default_profile_name(neu))
    _schreibe_profiles_datei(daten["active"], [*daten["profiles"], neu])
    reset_profile_cache()

    return neu


def rename_profile(profile_id: str, name: str) -> None:
    """Ändert nur den Anzeigenamen — das Verzeichnis heißt weiter wie bisher.

    Genau dafür ist die Kennung fest (ADR 015): ein Umbenennen des Ordners
    hieße, den ganzen Bestand zu verschieben und jeden `archive_path` in der
    Datenbank umzuschreiben.
    """
    if profile_id not in _read_profiles()["profiles"]:
        raise RuntimeError(f"Unbekanntes Profil: {profile_id}")

    if not name or not name.strip():
        raise RuntimeError("Der Name darf nicht leer sein.")

    _lege_profil_an(profile_id, name.strip())


def remove_profile(profile_id: str) -> Path:
    """Nimmt ein Profil aus der Liste — **ohne** Dateien zu löschen.

    Dieselbe Haltung wie beim Papierkorb: das Verzeichnis bleibt liegen und
    lässt sich später wieder eintragen. Wer es wirklich loswerden will, tut
    das bewusst im Dateimanager. Gibt das Verzeichnis zurück, damit die
    Oberfläche sagen kann, wo es liegt.
    """
    daten = _read_profiles()

    if profile_id not in daten["profiles"]:
        raise RuntimeError(f"Unbekanntes Profil: {profile_id}")

    # Deckt zugleich den letzten Eintrag ab: das einzige verbliebene Profil
    # ist zwangsläufig das geöffnete. Eine eigene Prüfung dafür wäre nie
    # erreichbar.
    if profile_id == daten["active"]:
        raise RuntimeError(
            "Das geöffnete Profil lässt sich nicht entfernen. Erst wechseln."
        )

    verweigere_bei_hintergrund_job("Profil entfernen")

    _schreibe_profiles_datei(
        daten["active"],
        [p for p in daten["profiles"] if p != profile_id],
    )
    reset_profile_cache()

    return _profiles_root() / profile_id


def verweigere_bei_hintergrund_job(vorhaben: str) -> None:
    """Sperre für alles, was den aktiven Bestand unter den Füßen wegzieht.

    Der Stapel-Import löst seine Pfade je Dokument neu auf und liefe nach
    einem Wechsel in den Bestand der anderen Person weiter. Die Abfrage beim
    Klick schließt das Zeitfenster praktisch — restlos wasserdicht wäre erst,
    den laufenden Import an sein Profil zu binden (siehe ADR 015).
    """
    laeuft = background_jobs.describe_running_job()

    if laeuft:
        raise RuntimeError(f"{vorhaben} nicht möglich: {laeuft}.")


def activate_profile(profile_id: str) -> None:
    """Wechselt das aktive Profil.

    Danach zeigen alle Pfade auf den neuen Bestand. Aufrufer sollten die
    Oberfläche neu aufbauen lassen — Seiten halten modulglobalen Zustand
    (z. B. den Suchfilter der Dokumentenliste), der zum vorherigen Bestand
    gehört.
    """
    daten = _read_profiles()

    if profile_id not in daten["profiles"]:
        raise RuntimeError(f"Unbekanntes Profil: {profile_id}")

    if profile_id == daten["active"]:
        return

    verweigere_bei_hintergrund_job("Profilwechsel")

    _schreibe_profiles_datei(profile_id, daten["profiles"])
    reset_profile_cache()

    # Das Schema-Flag gilt pro Prozess: ohne Reset liefe der erste Zugriff
    # auf die neue Datenbank an der Migration vorbei.
    reset_schema_state()

    logger.info("Profil gewechselt auf %s (%s)", profile_id, profile_name(profile_id))


def absolute_data_paths() -> list:
    """Config-Schlüssel mit absolutem Pfad — hebeln die Profiltrennung aus.

    Für die Warnung auf der Einstellungsseite: ein absoluter Pfad liegt für
    alle Profile im selben Verzeichnis, `resolve_path` lässt ihn bewusst
    stehen. Bewusst die ROHE Config, nicht `load_config()`: dort ist bereits
    absolutiert, und genau die Unterscheidung ist hier die Information.
    """
    from src.core.config import PATH_KEYS, config_path

    roh = yaml.safe_load(config_path().read_text(encoding="utf-8")) or {}

    return [
        f"{abschnitt}.{schluessel}"
        for abschnitt, schluessel in PATH_KEYS
        if (wert := (roh.get(abschnitt) or {}).get(schluessel))
        and Path(wert).is_absolute()
    ]

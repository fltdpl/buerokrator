"""Einmaliger Umzug eines profillosen Bestands in die Profilstruktur.

Bis ADR 015 lagen Datenbank, Archiv und Aliase direkt im App-Home. Seither
liegen sie unter `profiles/<kennung>/`. Dieses Modul holt einen Bestand aus
der alten Struktur nach — genau einmal je Installation.

**Warum das in der App liegt und nicht nur als Werkzeug.** Ursprünglich stand
der Umzug allein in `tools/port_to_profiles.py`, mit der Begründung: er läuft
einmal, wäre in der App also dauerhaftes Gewicht. Das übersah, wer ihn
braucht — wer aus einem Release-Paket installiert hat, besitzt weder Python
noch `tools/`. Für ihn zeigt die neue Fassung sonst still ein leeres Archiv,
während sein Bestand unberührt eine Ebene höher liegt. Das Werkzeug bleibt
als CLI bestehen; die Logik steht hier.

**Der Umzug ist der heikelste Vorgang am Bestand**, weil `archive_path`
absolut in der Datenbank steht: ein reines Verschieben der Ordner
hinterließe eine Datenbank, die auf nicht mehr vorhandene Dateien zeigt.
Deshalb wird kopiert, umgeschrieben, gegengeprüft — und erst ganz zum Schluss
`profiles.yaml` geschrieben. Diese Datei ist die Umschaltstelle; bricht etwas
vorher ab, bleibt der alte Bestand unangetastet.

Ein zusätzliches Backup gibt es bewusst NICHT: der Umzug kopiert und löscht
nie, die Originale wandern am Ende nach `vor-profilen/`. Das ist eine
stärkere Zusage als eine ZIP-Datei — und verdoppelt den Platzbedarf nicht
noch ein drittes Mal.
"""

import os
import shutil
import sqlite3
from pathlib import Path

import yaml

from src.core.app_home import (
    PROFILES_DIR,
    PROFILES_FILE,
    get_base_home,
    reset_profile_cache,
)
from src.core.config import PATH_KEYS, config_path
from src.core.logger import logger
from src.database.database import reset_schema_state
from src.services.profile_service import verweigere_bei_hintergrund_job

FIRST_ID = "1"
SECOND_ID = "2"

# Verzeichnis, in das die Originale nach dem Umzug wandern. Gelöscht wird
# nichts — dieselbe Haltung wie beim Papierkorb.
LEGACY_DIR = "vor-profilen"

# Profilgebundene Dinge, die NICHT in der Config stehen. Die Pfade spiegeln
# `organizer.trash.get_trash_dir` und `organizer.issuer_normalizer
# .aliases_path`; ein Test hält sie deckungsgleich.
FIXED_ITEMS = (
    "trash",
    "config/aussteller_aliase.yaml",
)


def _profiles_file() -> Path:
    return get_base_home() / PROFILES_FILE


def _profiles_root() -> Path:
    return get_base_home() / PROFILES_DIR


def profiles_enabled() -> bool:
    """Liegt schon eine Profilverwaltung vor?"""
    return _profiles_file().exists()


def legacy_bestand_gefunden() -> bool:
    """Liegt ein Bestand aus der Zeit vor ADR 015 in der Basis?

    Erkennungsmerkmal ist die Datenbank am ALTEN Ort: direkt in der Basis
    statt im Profil. Sie ist das einzige verlässliche Signal — ein Archiv
    kann leer sein, `.setup_done` gibt es auch bei frischen Installationen,
    und `profiles.yaml` fehlt bei einer Einzelperson ganz regulär.

    Ohne diese Erkennung ist der Fall still: die App legt im Profil eine
    leere Datenbank an und meldet „0 Dokumente archiviert", während der
    Bestand unberührt eine Ebene höher liegt.
    """
    if profiles_enabled():
        return False

    db_relativ = _db_relative_path()

    if not db_relativ:
        return False

    return (get_base_home() / db_relativ).exists()


def _data_paths() -> tuple:
    """(relative, absolute) Datenpfade, so wie sie ROH in der Config stehen.

    Bewusst die rohe Datei, nicht `load_config()`: dort sind die Werte schon
    absolutiert, und genau die Unterscheidung relativ/absolut ist hier die
    entscheidende Information.
    """
    raw = yaml.safe_load(config_path().read_text(encoding="utf-8")) or {}
    relative = []
    absolute = []

    for section, key in PATH_KEYS:
        value = (raw.get(section) or {}).get(key)

        if not value:
            continue

        if Path(value).is_absolute():
            absolute.append(f"{section}.{key}")

        else:
            relative.append(str(value))

    return relative, absolute


def _relative_data_paths() -> list:
    relative, absolute = _data_paths()

    if absolute:
        raise RuntimeError(
            "Profile brauchen relative Pfade in den Einstellungen. Absolut "
            f"eingetragen ist: {', '.join(absolute)}. Ein absoluter Pfad "
            "läge für alle Personen im selben Verzeichnis — die Trennung "
            "wäre damit aufgehoben."
        )

    return relative


def _copy_database(source: Path, target: Path) -> None:
    """DB über die SQLite-API kopieren, nicht als Datei.

    Im WAL-Modus stehen committete Transaktionen in der -wal-Datei, bis ein
    Checkpoint läuft. Eine reine Dateikopie lieferte dann still einen Stand
    ohne die zuletzt importierten Dokumente — derselbe Fehler, der beim
    Backup schon einmal steckte (siehe backup_service).
    """
    target.parent.mkdir(parents=True, exist_ok=True)

    quelle = sqlite3.connect(source)

    try:
        ziel = sqlite3.connect(target)

        try:
            quelle.backup(ziel)

        finally:
            ziel.close()

    finally:
        quelle.close()

    # Die Kopie entsteht neu und erbt sonst die umask. Sie enthält die
    # OCR-Volltexte aller Dokumente — dieselbe Zusage wie beim Original.
    try:
        os.chmod(target, 0o600)

    except OSError:
        pass


def _rewrite_archive_paths(
    db_path: Path, alt: Path, neu: Path, alt_basis: Path
) -> dict:
    """Setzt `archive_path` vom alten auf das neue Archiv um.

    ⚠️ **Relative Pfade müssen mit.** Ältere Importe haben sie hinterlassen;
    sie sind gegen das App-Home gemeint, lösen aber gegen das
    Arbeitsverzeichnis auf. Beim ersten Port am echten Bestand blieben sie
    stehen und zeigten danach ins Leere — die Gegenprobe merkte es nicht,
    weil der Prozess zufällig im alten Basisverzeichnis lief. Hier werden sie
    erst gegen die alte Basis absolut gemacht und dann wie alle anderen
    umgesetzt; danach ist **kein** Pfad mehr relativ.
    """
    altes_praefix = f"{alt}/"
    neues_praefix = f"{neu}/"

    conn = sqlite3.connect(db_path)

    try:
        cursor = conn.cursor()
        umgeschrieben = 0
        unberuehrt = 0

        for document_id, pfad in cursor.execute(
            "SELECT id, archive_path FROM documents"
        ).fetchall():
            if not pfad:
                unberuehrt += 1
                continue

            absolut = str(pfad if Path(pfad).is_absolute() else alt_basis / pfad)

            if absolut.startswith(altes_praefix):
                neuer = absolut.replace(altes_praefix, neues_praefix, 1)

            elif absolut != pfad:
                # Lag außerhalb des Archivs, war aber relativ: wenigstens
                # eindeutig machen. Die Gegenprobe entscheidet dann.
                neuer = absolut

            else:
                unberuehrt += 1
                continue

            cursor.execute(
                "UPDATE documents SET archive_path = ? WHERE id = ?",
                (neuer, document_id),
            )
            umgeschrieben += 1

        conn.commit()

        return {"umgeschrieben": umgeschrieben, "unberuehrt": unberuehrt}

    finally:
        conn.close()


def _pruefe_bestand(db_path: Path, erwartete_zeilen: int) -> int:
    """Gegenprobe: gleiche Zeilenzahl, und jede Datei liegt am neuen Ort."""
    conn = sqlite3.connect(db_path)

    try:
        pfade = [
            row[0]
            for row in conn.execute("SELECT archive_path FROM documents").fetchall()
        ]

    finally:
        conn.close()

    if len(pfade) != erwartete_zeilen:
        raise RuntimeError(
            f"Umzug abgebrochen: die Kopie hat {len(pfade)} Zeilen, "
            f"das Original {erwartete_zeilen}."
        )

    # Zuerst: kein Pfad darf relativ geblieben sein. Ein relativer Pfad löst
    # gegen das Arbeitsverzeichnis auf — die Existenzprüfung darunter wäre
    # dann zufällig grün, je nachdem, wo der Prozess gerade steht. Genau so
    # ging der erste Port am echten Bestand halb daneben.
    relativ = [pfad for pfad in pfade if pfad and not Path(pfad).is_absolute()]

    if relativ:
        raise RuntimeError(
            f"Umzug abgebrochen: {len(relativ)} Dokument(e) haben nach dem "
            "Umschreiben noch einen relativen Pfad."
        )

    fehlend = [pfad for pfad in pfade if pfad and not Path(pfad).exists()]

    if fehlend:
        raise RuntimeError(
            f"Umzug abgebrochen: {len(fehlend)} Dokument(e) liegen nicht am "
            f"neuen Ort, zuerst {fehlend[0]}."
        )

    return len(pfade)


def _zeilenzahl(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)

    try:
        return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    finally:
        conn.close()


def _lege_profil_an(profile_id: str, name: str) -> Path:
    verzeichnis = _profiles_root() / profile_id
    verzeichnis.mkdir(parents=True, exist_ok=True)
    (verzeichnis / "profile.yaml").write_text(
        yaml.safe_dump({"name": name}, allow_unicode=True),
        encoding="utf-8",
    )

    return verzeichnis


def enable_profiles(erster_name=None, zweiter_name=None, vorpruefung=None) -> dict:
    """Legt die Profilstruktur an und zieht den bisherigen Bestand um.

    Reihenfolge ist Absicht (ADR 015): kopieren, Pfade umschreiben,
    gegenprüfen, `profiles.yaml` ZULETZT, danach erst die Originale
    beiseiteräumen. Bricht etwas vorher ab, bleibt der alte Bestand
    unangetastet und die App läuft unverändert weiter.

    `vorpruefung` ist die Sperre gegen einen Schreiber am selben Bestand.
    In der App ist das der laufende Hintergrund-Job (Standard); das
    CLI-Werkzeug läuft in einem eigenen Prozess und reicht stattdessen seine
    Port-Prüfung herein — es kann von einem laufenden Import nichts wissen.
    """
    if profiles_enabled():
        raise RuntimeError("Es gibt bereits Profile.")

    (vorpruefung or (lambda: verweigere_bei_hintergrund_job("Umzug")))()

    basis = get_base_home()
    relative = _relative_data_paths()
    profiles_root = _profiles_root()

    if profiles_root.exists():
        raise RuntimeError(
            f"{profiles_root} existiert bereits — Rest eines abgebrochenen "
            "Umzugs? Bitte prüfen und entfernen."
        )

    erstes = profiles_root / FIRST_ID
    umgezogen = []
    bericht = {"umgeschrieben": 0, "geprueft": 0, "unberuehrt": 0}

    try:
        _lege_profil_an(FIRST_ID, erster_name or "Benutzer 1")
        _lege_profil_an(SECOND_ID, zweiter_name or "Benutzer 2")

        # 1. Kopieren. Die Datenbank braucht den SQLite-Weg (WAL), alles
        #    andere sind schlichte Dateien.
        db_relativ = _db_relative_path()

        for relativ in [*relative, *FIXED_ITEMS]:
            quelle = basis / relativ
            ziel = erstes / relativ

            if not quelle.exists():
                continue

            if relativ == db_relativ:
                _copy_database(quelle, ziel)

            elif quelle.is_dir():
                shutil.copytree(quelle, ziel)

            else:
                ziel.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(quelle, ziel)

            umgezogen.append(relativ)

        # 2. Archivpfade in der KOPIE umschreiben, 3. gegenprüfen.
        archiv_relativ = _config_relative("paths", "archive")
        db_quelle = basis / db_relativ
        db_ziel = erstes / db_relativ

        if db_ziel.exists() and archiv_relativ:
            erwartet = _zeilenzahl(db_quelle)
            bericht.update(
                _rewrite_archive_paths(
                    db_ziel,
                    basis / archiv_relativ,
                    erstes / archiv_relativ,
                    basis,
                )
            )
            bericht["geprueft"] = _pruefe_bestand(db_ziel, erwartet)

    except Exception:
        # Vor der Umschaltstelle: das halbe Profilverzeichnis wieder
        # entfernen, damit ein zweiter Versuch sauber startet. Die
        # Originale wurden bis hier nur gelesen.
        shutil.rmtree(profiles_root, ignore_errors=True)
        raise

    # 4. Umschaltstelle. Ab hier arbeitet die App im Profil.
    _schreibe_profiles_datei(FIRST_ID, [FIRST_ID, SECOND_ID])
    reset_profile_cache()

    # Das Schema-Flag gilt pro Prozess, nicht pro Datenbank: läuft der Umzug
    # aus der App heraus, liefe der erste Zugriff auf die umgezogene Kopie
    # sonst an der Migration vorbei. Im eigenen Prozess des Werkzeugs ist der
    # Aufruf wirkungslos.
    reset_schema_state()

    # 5. Originale beiseiteräumen — nicht löschen.
    beiseite = basis / LEGACY_DIR
    for relativ in umgezogen:
        _raeume_beiseite(basis / relativ, beiseite / relativ)

    logger.info(
        "Profile eingerichtet: %s Dokumentpfade umgeschrieben, "
        "Altbestand nach %s",
        bericht["umgeschrieben"],
        beiseite,
    )

    bericht["altbestand"] = beiseite
    bericht["profil"] = erstes

    return bericht


# Seitendateien von SQLite. Sie gehören zur Datenbank: bleibt eine -wal
# zurück, ist der beiseitegeräumte Altbestand unvollständig — genau die
# Sicherung, auf die man im Zweifel zurückgreifen will.
_DB_SEITENDATEIEN = ("-wal", "-shm", "-journal")


def _raeume_beiseite(quelle: Path, ziel: Path) -> None:
    """Verschiebt ein Original zur Seite, samt SQLite-Seitendateien.

    Räumt danach ein leer gewordenes Elternverzeichnis ab, damit am alten
    Ort nichts stehen bleibt, was die App versehentlich neu befüllen könnte.
    """
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(quelle), str(ziel))

    if not ziel.is_dir():
        for endung in _DB_SEITENDATEIEN:
            nebendatei = quelle.with_name(quelle.name + endung)

            if nebendatei.exists():
                shutil.move(str(nebendatei), str(ziel.with_name(ziel.name + endung)))

        try:
            quelle.parent.rmdir()

        except OSError:
            # Nicht leer (oder gar nicht da) — dann bleibt es, wie es ist.
            pass


def _schreibe_profiles_datei(aktiv: str, profile: list) -> None:
    _profiles_file().write_text(
        yaml.safe_dump({"active": aktiv, "profiles": list(profile)}),
        encoding="utf-8",
    )


def _config_relative(section: str, key: str) -> "str | None":
    raw = yaml.safe_load(config_path().read_text(encoding="utf-8")) or {}
    value = (raw.get(section) or {}).get(key)

    return str(value) if value else None


def _db_relative_path() -> "str | None":
    return _config_relative("database", "path")

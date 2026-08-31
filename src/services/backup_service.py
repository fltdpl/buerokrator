"""Backup: Datenbank + Archivordner als eine ZIP-Datei sichern.

Framework-neutral und offline — schreibt nur an einen lokalen Zielort. Der
reine `create_backup` ist ohne App-Kontext testbar; `run_backup` verdrahtet
ihn mit der Konfiguration.
"""

import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
import zlib
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from src.core.app_home import get_app_home
from src.core.config import load_config
from src.core.exceptions import BuerokratorError
from src.organizer.filename_builder import get_unique_target_path
from src.core.logger import logger
from src.services.archive_repair import repariere_archivpfade

# Ab wann eine Sicherung als überfällig gilt (Tage). Drei Monate, weil der
# Bestand stapelweise wächst und ein realistischer Rhythmus bei drei bis
# sechs Monaten liegt: eine kürzere Frist mahnte auch dann, wenn seit der
# letzten Sicherung nichts dazugekommen ist — und eine Mahnung, die meistens
# unbegründet ist, wird weggesehen.
BACKUP_WARNUNG_TAGE = 90

# Wie viele Sicherungen beim Aufräumen stehen bleiben. Drei decken bei einem
# Rhythmus von drei bis sechs Monaten rund ein Jahr ab — genug, um auch einen
# Schaden zu überstehen, der erst nach zwei Sicherungen auffällt.
SICHERUNGEN_BEHALTEN = 3

# Unterordner im Papierkorb. Bewusst getrennt vom Dokument-Papierkorb: der
# bietet seinen Inhalt zum Wiederherstellen in die Inbox an, und eine
# Backup-ZIP dort wäre ein Dokument, das importiert werden will.
SICHERUNGS_PAPIERKORB = "sicherungen"

# Zeitstempel im Dateinamen, z. B. buerokrator_backup_20260731_101500.zip.
_ZEITSTEMPEL = re.compile(r"(\d{8}_\d{6})")


def backup_ziel(config=None):
    """Ordner, in dem die Sicherungen liegen (aus der Konfiguration).

    Eine Stelle für alle Konsumenten: Dashboard und Einstellungen müssen
    denselben Ort meinen, sonst zeigt die eine Fläche ein Alter, das die
    andere nicht erklären kann. Der Wert ist nach `load_config()` bereits
    absolut und gegen das Profil aufgelöst.
    """
    config = config if config is not None else load_config()

    return (config.get("backup") or {}).get("target") or "./backups"


def _zeitpunkt(path):
    """Wann die Sicherung entstanden ist — aus dem Namen, sonst aus der mtime.

    Die mtime lügt, sobald eine Sicherung kopiert wurde: vom Stick zurück-
    geholt oder aus der Cloud geladen trägt eine monatealte Datei das Datum
    von heute. Der Name trägt den Zeitpunkt der Erstellung und wandert mit.
    Von Hand benannte Sicherungen fallen auf die mtime zurück.
    """
    treffer = _ZEITSTEMPEL.search(path.name)

    if treffer:
        try:
            return datetime.strptime(treffer.group(1), "%Y%m%d_%H%M%S")

        except ValueError:
            pass

    return datetime.fromtimestamp(path.stat().st_mtime)


def backup_alter_tage(target_dir, now=None):
    """Volle Tage seit der jüngsten Sicherung — None, wenn es keine gibt.

    Der Unterschied zwischen „keine" und „0 Tage" trägt die Beschriftung in
    der Oberfläche und darf hier nicht eingeebnet werden. Angefangene Tage
    zählen nicht mit; eine Sicherung aus der Zukunft (verstellte Uhr,
    kopierte Datei) ergibt 0 statt eines negativen Alters.
    """
    backups = list_backups(target_dir)

    if not backups:
        return None

    now = now or datetime.now()

    return max((now - backups[0]["zeitpunkt"]).days, 0)


def _default_backup_name(now):
    return f"buerokrator_backup_{now.strftime('%Y%m%d_%H%M%S')}.zip"


@contextmanager
def _database_snapshot(db_path, workspace_dir):
    """Konsistente Momentaufnahme der Datenbank als temporäre Datei.

    Bewusst NICHT die .db-Datei kopieren: im WAL-Modus stehen committete
    Transaktionen in der -wal-Datei, bis ein Checkpoint läuft — und der
    läuft nicht, solange eine andere Verbindung offen ist (Stapel-Import).
    Eine reine Dateikopie lieferte dann still eine Sicherung ohne die
    zuletzt importierten Dokumente.

    sqlite3.Connection.backup() liest über die SQLite-API und schließt den
    WAL-Inhalt ein; es ist außerdem gegen parallele Schreiber sicher (kein
    halb geschriebener Zustand). Ein defektes DB-File lässt die
    sqlite3.DatabaseError durch — eine Sicherung, die die Datenbank nicht
    lesen kann, darf nicht scheinbar gelingen.

    Der Snapshot entsteht bewusst in workspace_dir (dem Backup-Zielordner)
    und NICHT in /tmp: die Datei ist eine vollständige Kopie der DB samt
    aller OCR-Volltexte. Sie gehört nicht auf ein fremdes Dateisystem, das
    der Nutzer nicht als privat einstuft. mkdtemp legt das Verzeichnis mit
    0700 an; der Snapshot ist damit nur für den Besitzer lesbar.
    """
    with tempfile.TemporaryDirectory(dir=workspace_dir) as workspace:
        snapshot = Path(workspace) / db_path.name

        source = sqlite3.connect(db_path)

        try:
            target = sqlite3.connect(snapshot)

            try:
                source.backup(target)

            finally:
                target.close()

        finally:
            source.close()

        yield snapshot


def pruefe_sicherung(zip_path, erwartet):
    """Liest die frisch geschriebene ZIP zurück und beanstandet Schäden.

    Geprüft wird beides: die CRC-Summe jedes Eintrags (`testzip` liest dafür
    alle Daten) und die Vollständigkeit der Liste. Eine volle Platte oder ein
    abbrechender Wechseldatenträger hinterlassen sonst eine Datei, die
    aussieht wie eine Sicherung — und das fällt erst beim Wiederherstellen
    auf, also Jahre später und im schlechtesten Moment.
    """
    try:
        with zipfile.ZipFile(zip_path) as archive:
            beschaedigt = archive.testzip()
            vorhanden = set(archive.namelist())

    # Je nachdem, wo der Schaden sitzt, meldet testzip ihn als Rückgabe oder
    # das Auspacken bricht ab. Beides ist derselbe Befund und gehört als
    # verständlicher Satz in die Oberfläche, nicht als zlib-Meldung.
    except (zipfile.BadZipFile, zlib.error, EOFError, OSError) as fehler:
        raise BuerokratorError(
            f"Die Sicherung ist beschädigt oder unlesbar: {fehler}"
        ) from fehler

    if beschaedigt is not None:
        raise BuerokratorError(
            f"Die Sicherung ist beschädigt (Prüfsumme bei {beschaedigt})."
        )

    fehlend = sorted(set(erwartet) - vorhanden)

    if fehlend:
        raise BuerokratorError(
            "Die Sicherung ist unvollständig, es fehlen: " + ", ".join(fehlend)
        )


def create_backup(db_path, archive_dir, target_dir, backup_name, config_dir=None):
    """Packt DB, Archivordner und Profil-Konfiguration in eine ZIP-Datei.

    Die DB liegt im Archiv unter `database/`, das Archiv unter `archive/`,
    die Konfiguration des Profils unter `config/`. Fehlt eine Quelle, wird
    sie übersprungen (ein frisches System hat evtl. noch kein Archiv).

    `config_dir` ist der `config`-Ordner des APP-HOME, nicht der der
    Installation (ADR 015): gesichert wird der Bestand einer Person, und
    dazu gehören die Aussteller-Aliase — Handarbeit von Monaten, die in
    keiner Datenbank steht. Die `settings.yaml` der Installation gehört
    bewusst NICHT dazu; sie trägt Pfade, die am neuen Ort falsch wären.

    Gibt den Pfad der erzeugten ZIP-Datei zurück.
    """
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    zip_path = target_dir / backup_name

    db_path = Path(db_path)
    archive_dir = Path(archive_dir)

    geschrieben = []

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        if db_path.exists():
            with _database_snapshot(db_path, target_dir) as snapshot:
                arcname = f"database/{db_path.name}"
                archive.write(snapshot, arcname=arcname)
                geschrieben.append(arcname)

        if archive_dir.exists():
            for file in sorted(archive_dir.rglob("*")):
                if file.is_file():
                    arcname = Path("archive") / file.relative_to(archive_dir)
                    archive.write(file, arcname=str(arcname))
                    geschrieben.append(str(arcname))

        if config_dir is not None and Path(config_dir).exists():
            config_dir = Path(config_dir)

            for file in sorted(config_dir.rglob("*")):
                if file.is_file():
                    arcname = Path("config") / file.relative_to(config_dir)
                    archive.write(file, arcname=str(arcname))
                    geschrieben.append(str(arcname))

    # Modul-Attribut statt direktem Aufruf: so lässt sich das Scheitern der
    # Prüfung im Test auslösen, ohne eine Datei kaputtmachen zu müssen.
    try:
        pruefe_sicherung(zip_path, geschrieben)

    except Exception:
        # Nicht löschen (Projektlinie), aber aus dem Weg räumen: als *.zip
        # gälte die kaputte Datei als jüngste Sicherung und das Dashboard
        # gäbe Entwarnung für einen Datenmüllhaufen.
        os.replace(zip_path, zip_path.with_name(zip_path.name + ".unvollstaendig"))
        raise

    # Backup enthält DB (Volltexte) + alle Dokumente im Klartext — nur für
    # den Besitzer lesbar.
    try:
        os.chmod(zip_path, 0o600)

    except OSError:
        pass

    return zip_path


def run_backup():
    """Erstellt ein Backup anhand der Konfiguration und gibt den Pfad zurück."""
    config = load_config()

    db_path = config["database"]["path"]
    archive_dir = config["paths"]["archive"]
    target_dir = backup_ziel(config)

    zip_path = create_backup(
        db_path=db_path,
        archive_dir=archive_dir,
        config_dir=get_app_home() / "config",
        target_dir=target_dir,
        backup_name=_default_backup_name(datetime.now()),
    )

    size = zip_path.stat().st_size
    logger.info(f"Backup erstellt: {zip_path} ({size} Bytes)")

    return zip_path


def list_backups(target_dir):
    """Vorhandene Backup-ZIPs im Zielordner, neueste zuerst (Plain Data)."""
    target_dir = Path(target_dir)

    if not target_dir.exists():
        return []

    backups = []

    for path in target_dir.glob("*.zip"):
        backups.append(
            {
                "path": str(path),
                "name": path.name,
                "size_mb": path.stat().st_size / 1024 / 1024,
                "mtime": path.stat().st_mtime,
                "zeitpunkt": _zeitpunkt(path),
            }
        )

    return sorted(backups, key=lambda eintrag: eintrag["zeitpunkt"], reverse=True)


def restore_backup(zip_path, db_path, archive_dir, config_dir=None, now=None):
    """Stellt Datenbank, Archiv und Profil-Konfiguration wieder her.

    Sicherheitsprinzip: NICHTS wird gelöscht. Der aktuelle Stand wird
    beiseitegelegt (DB als pre_restore_<ts>.db neben der DB, Archiv- und
    Konfigurationsordner als <name>_vor_wiederherstellung_<ts>) und erst
    dann aus der ZIP extrahiert.

    Sicherungen aus früheren Fassungen tragen kein `config/`. Sie bleiben
    gültig — und lassen die vorhandene Aliasdatei dann unangetastet stehen,
    statt sie gegen nichts einzutauschen. Der Alias-Cache greift von selbst
    neu, weil er über mtime und Größe der Datei geschlüsselt ist.

    ⚠️ **Danach müssen die Archivpfade neu gebunden werden.** `archive_path`
    steht absolut in der Datenbank; wird eine Sicherung an einem ANDEREN Ort
    eingespielt (frische Installation, zweiter Rechner), liegen die Dateien
    zwar richtig, aber jede Zeile zeigt auf den Ort von der Sicherungszeit.
    Der Fehler war still — alle Werte richtig, nur das PDF "nicht gefunden".

    Gibt Plain Data zurück: {"database": bool, "archive_files": int,
    "archive_pfade_repariert": int, "archive_pfade_ungeloest": int}.
    """
    zip_path = Path(zip_path)
    db_path = Path(db_path)
    archive_dir = Path(archive_dir)
    config_dir = Path(config_dir) if config_dir is not None else None
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")

    with zipfile.ZipFile(zip_path) as backup:
        names = backup.namelist()
        db_members = [
            n for n in names if n.startswith("database/") and not n.endswith("/")
        ]
        archive_members = [
            n for n in names if n.startswith("archive/") and not n.endswith("/")
        ]
        config_members = [
            n for n in names if n.startswith("config/") and not n.endswith("/")
        ]

        if len(db_members) != 1:
            raise ValueError(
                "Keine gültige Buerokrator-Sicherung: die ZIP-Datei muss genau "
                "eine Datenbank unter database/ enthalten."
            )

        # Aktuellen Stand beiseitelegen (inkl. WAL/SHM-Nebendateien der DB —
        # sonst gehörte deren Inhalt zur alten DB und korrumpierte die neue).
        if db_path.exists():
            db_path.rename(db_path.with_name(f"pre_restore_{timestamp}.db"))

        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(db_path) + suffix)
            if sidecar.exists():
                sidecar.rename(
                    sidecar.with_name(f"pre_restore_{timestamp}.db{suffix}")
                )

        if archive_dir.exists():
            archive_dir.rename(
                archive_dir.with_name(f"{archive_dir.name}_vor_wiederherstellung_{timestamp}")
            )

        # Nur beiseitelegen, wenn die Sicherung überhaupt etwas mitbringt.
        if config_members and config_dir is not None and config_dir.exists():
            config_dir.rename(
                config_dir.with_name(
                    f"{config_dir.name}_vor_wiederherstellung_{timestamp}"
                )
            )

        # Datenbank extrahieren (Zielname aus der Config, nicht aus der ZIP).
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with backup.open(db_members[0]) as source, open(db_path, "wb") as target:
            shutil.copyfileobj(source, target)

        try:
            os.chmod(db_path, 0o600)

        except OSError:
            pass

        # Archiv und Konfiguration extrahieren; die Pfade laufen durch
        # dieselbe Traversal-Prüfung.
        auszupacken = [("archive", archive_members, archive_dir)]

        if config_dir is not None:
            auszupacken.append(("config", config_members, config_dir))

        for praefix, members, ziel in auszupacken:
            for member in members:
                relative = Path(member).relative_to(praefix)

                if ".." in relative.parts:
                    raise ValueError(f"Unsicherer Pfad in der ZIP-Datei: {member}")

                target_file = ziel / relative
                target_file.parent.mkdir(parents=True, exist_ok=True)

                with backup.open(member) as source, open(target_file, "wb") as target:
                    shutil.copyfileobj(source, target)

    # Pfade an das Archiv HIER binden. Ohne Sicherung: der alte Stand liegt
    # als pre_restore bereits beiseite. Die Basis ist das Elternverzeichnis
    # des Archivs — dagegen sind die alten relativen Einträge gemeint.
    #
    # Ein Fehler dabei darf die Wiederherstellung NICHT scheitern lassen: die
    # Dateien liegen dann bereits am Ziel, und ein Abbruch hier ließe den
    # Nutzer mit halb ausgepacktem Bestand zurück. Die Bindung ist über
    # "Archivpfade reparieren" jederzeit nachholbar.
    try:
        pfade = repariere_archivpfade(
            db_path, archive_dir, basis=archive_dir.parent, sichern=False
        )

    except (RuntimeError, sqlite3.Error) as error:
        logger.warning(
            "Archivpfade nach der Wiederherstellung nicht gebunden (%s) — "
            "über 'Archivpfade reparieren' nachholbar.",
            error,
        )
        pfade = {"repariert": 0, "ungeloest": 0}

    logger.info(
        f"Backup wiederhergestellt: {zip_path} "
        f"({len(archive_members)} Archivdateien); alter Stand beiseitegelegt "
        f"(pre_restore_{timestamp}); {pfade['repariert']} Archivpfade neu "
        f"gebunden, {pfade['ungeloest']} ungelöst"
    )

    return {
        "database": True,
        "archive_files": len(archive_members),
        "config_files": len(config_members) if config_dir is not None else 0,
        "archive_pfade_repariert": pfade["repariert"],
        "archive_pfade_ungeloest": pfade["ungeloest"],
    }


def run_restore(zip_path):
    """Stellt ein Backup anhand der Konfiguration wieder her.

    Setzt danach das Schema-Flag zurück, damit der nächste DB-Zugriff die
    wiederhergestellte (ggf. ältere) Datenbank migriert.
    """
    config = load_config()

    result = restore_backup(
        zip_path,
        db_path=config["database"]["path"],
        archive_dir=config["paths"]["archive"],
        config_dir=get_app_home() / "config",
    )

    # Die Migration ist prozessweit einmalig — nach dem Austausch der DB muss
    # sie erneut laufen (die wiederhergestellte DB kann älter sein).
    import src.database.database as database

    database._schema_ready = False

    return result


# --------------------------------------------------------------- Aufräumen


def _groesse(pfad):
    """Bytes einer Datei oder eines ganzen Verzeichnisbaums."""
    if pfad.is_file():
        return pfad.stat().st_size

    gesamt = 0

    for eintrag in pfad.rglob("*"):
        try:
            if eintrag.is_file():
                gesamt += eintrag.stat().st_size

        except OSError:
            continue

    return gesamt


def _kandidat(pfad, art):
    return {
        "pfad": str(pfad),
        "name": pfad.name,
        "groesse": _groesse(pfad),
        "art": art,
    }


def aufraeum_kandidaten(
    target_dir, db_path, archive_dir, config_dir=None, behalten=SICHERUNGEN_BEHALTEN
):
    """Was weg kann, ohne den Bestand anzutasten (Plain Data, größte zuerst).

    Zwei Arten: `sicherung` sind die Vollkopien jenseits der jüngsten
    `behalten` (plus alles, was als `.unvollstaendig` liegen geblieben ist —
    das ist per Definition wertlos und zählt nicht mit). `rest` sind die
    Stände, die eine frühere Wiederherstellung beiseitegelegt hat.

    ⚠️ Der lebende Bestand darf hier NIE auftauchen. Deshalb wird nur nach
    den festen Präfixen gesucht, die diese Datei selbst vergibt — nie
    nach Alter oder Größe.
    """
    target_dir = Path(target_dir)
    db_path = Path(db_path)
    archive_dir = Path(archive_dir)

    kandidaten = []

    for eintrag in list_backups(target_dir)[behalten:]:
        kandidaten.append(_kandidat(Path(eintrag["path"]), "sicherung"))

    if target_dir.exists():
        for pfad in sorted(target_dir.glob("*.unvollstaendig")):
            kandidaten.append(_kandidat(pfad, "sicherung"))

    reste = list(db_path.parent.glob("pre_restore_*"))
    reste += list(
        archive_dir.parent.glob(f"{archive_dir.name}_vor_wiederherstellung_*")
    )

    if config_dir is not None:
        config_dir = Path(config_dir)
        reste += list(
            config_dir.parent.glob(f"{config_dir.name}_vor_wiederherstellung_*")
        )

    for pfad in sorted(reste):
        kandidaten.append(_kandidat(pfad, "rest"))

    return sorted(kandidaten, key=lambda eintrag: eintrag["groesse"], reverse=True)


def in_papierkorb(kandidaten, trash_dir):
    """Verschiebt Kandidaten in den Sicherungs-Papierkorb (löscht nichts).

    Verschieben statt Löschen ist Projektlinie: ein Fehlklick darf keine
    Kopie von Originaldokumenten vernichten. Namenskollisionen werden
    aufgelöst, damit der Papierkorb nichts überschreibt, was schon in ihm
    liegt.
    """
    trash_dir = Path(trash_dir)
    anzahl = 0
    bytes_gesamt = 0

    for eintrag in kandidaten:
        quelle = Path(eintrag["pfad"])

        if not quelle.exists():
            continue

        trash_dir.mkdir(parents=True, exist_ok=True)
        ziel = get_unique_target_path(trash_dir / quelle.name)
        shutil.move(str(quelle), str(ziel))

        anzahl += 1
        bytes_gesamt += eintrag["groesse"]

    logger.info(
        f"Aufgeräumt: {anzahl} Eintrag/Einträge in den Sicherungs-Papierkorb "
        f"({bytes_gesamt} Bytes)"
    )

    return {"anzahl": anzahl, "bytes": bytes_gesamt}


def papierkorb_inhalt(trash_dir):
    """Was im Sicherungs-Papierkorb liegt (oberste Ebene, Plain Data)."""
    trash_dir = Path(trash_dir)

    if not trash_dir.exists():
        return {"anzahl": 0, "bytes": 0}

    eintraege = list(trash_dir.iterdir())

    return {
        "anzahl": len(eintraege),
        "bytes": sum(_groesse(pfad) for pfad in eintraege),
    }


def leere_papierkorb(trash_dir):
    """Löscht den Sicherungs-Papierkorb endgültig.

    Der zweite Ort im Projekt, an dem wirklich etwas verschwindet — und wie
    der erste nur durch eine ausdrückliche Nutzeraktion erreichbar.
    """
    trash_dir = Path(trash_dir)
    inhalt = papierkorb_inhalt(trash_dir)

    if not trash_dir.exists():
        return inhalt

    for pfad in trash_dir.iterdir():
        if pfad.is_dir():
            shutil.rmtree(pfad)

        else:
            pfad.unlink()

    logger.info(
        f"Sicherungs-Papierkorb geleert: {inhalt['anzahl']} Eintrag/Einträge, "
        f"{inhalt['bytes']} Bytes"
    )

    return inhalt


def sicherungs_papierkorb():
    """Ort des Sicherungs-Papierkorbs im App-Home."""
    return get_app_home() / "trash" / SICHERUNGS_PAPIERKORB


def aufraeum_uebersicht():
    """Kandidaten und Papierkorb-Inhalt in einem Aufruf (Plain Data)."""
    config = load_config()

    return {
        "kandidaten": aufraeum_kandidaten(
            target_dir=backup_ziel(config),
            db_path=config["database"]["path"],
            archive_dir=config["paths"]["archive"],
            config_dir=get_app_home() / "config",
        ),
        "papierkorb": papierkorb_inhalt(sicherungs_papierkorb()),
    }


def run_aufraeumen():
    """Verschiebt alle Kandidaten in den Sicherungs-Papierkorb."""
    return in_papierkorb(
        aufraeum_uebersicht()["kandidaten"], sicherungs_papierkorb()
    )


def run_papierkorb_leeren():
    return leere_papierkorb(sicherungs_papierkorb())

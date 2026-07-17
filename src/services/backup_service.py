"""Backup: Datenbank + Archivordner als eine ZIP-Datei sichern.

Framework-neutral und offline — schreibt nur an einen lokalen Zielort. Der
reine `create_backup` ist ohne App-Kontext testbar; `run_backup` verdrahtet
ihn mit der Konfiguration.
"""

import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from src.core.config import load_config
from src.core.logger import logger


def _default_backup_name(now):
    return f"buerokrator_backup_{now.strftime('%Y%m%d_%H%M%S')}.zip"


def create_backup(db_path, archive_dir, target_dir, backup_name):
    """Packt DB-Datei und Archivordner in eine ZIP-Datei unter target_dir.

    Die DB liegt im Archiv unter `database/`, das Archiv unter `archive/`.
    Fehlt eine Quelle, wird sie übersprungen (ein frisches System hat evtl.
    noch kein Archiv). Gibt den Pfad der erzeugten ZIP-Datei zurück.
    """
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    zip_path = target_dir / backup_name

    db_path = Path(db_path)
    archive_dir = Path(archive_dir)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        if db_path.exists():
            archive.write(db_path, arcname=f"database/{db_path.name}")

        if archive_dir.exists():
            for file in sorted(archive_dir.rglob("*")):
                if file.is_file():
                    arcname = Path("archive") / file.relative_to(archive_dir)
                    archive.write(file, arcname=str(arcname))

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
    target_dir = config.get("backup", {}).get("target", "./backups")

    zip_path = create_backup(
        db_path=db_path,
        archive_dir=archive_dir,
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

    for path in sorted(
        target_dir.glob("*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        backups.append(
            {
                "path": str(path),
                "name": path.name,
                "size_mb": path.stat().st_size / 1024 / 1024,
            }
        )

    return backups


def restore_backup(zip_path, db_path, archive_dir, now=None):
    """Stellt Datenbank + Archiv aus einer Backup-ZIP wieder her.

    Sicherheitsprinzip: NICHTS wird gelöscht. Der aktuelle Stand wird
    beiseitegelegt (DB als pre_restore_<ts>.db neben der DB, Archivordner
    als <archiv>_vor_wiederherstellung_<ts>) und erst dann aus der ZIP
    extrahiert. Gibt Plain Data zurück: {"database": bool, "archive_files": int}.
    """
    zip_path = Path(zip_path)
    db_path = Path(db_path)
    archive_dir = Path(archive_dir)
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")

    with zipfile.ZipFile(zip_path) as backup:
        names = backup.namelist()
        db_members = [
            n for n in names if n.startswith("database/") and not n.endswith("/")
        ]
        archive_members = [
            n for n in names if n.startswith("archive/") and not n.endswith("/")
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

        # Datenbank extrahieren (Zielname aus der Config, nicht aus der ZIP).
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with backup.open(db_members[0]) as source, open(db_path, "wb") as target:
            shutil.copyfileobj(source, target)

        try:
            os.chmod(db_path, 0o600)

        except OSError:
            pass

        # Archiv extrahieren; Pfade laufen durch eine Traversal-Prüfung.
        for member in archive_members:
            relative = Path(member).relative_to("archive")

            if ".." in relative.parts:
                raise ValueError(f"Unsicherer Pfad in der ZIP-Datei: {member}")

            target_file = archive_dir / relative
            target_file.parent.mkdir(parents=True, exist_ok=True)

            with backup.open(member) as source, open(target_file, "wb") as target:
                shutil.copyfileobj(source, target)

    logger.info(
        f"Backup wiederhergestellt: {zip_path} "
        f"({len(archive_members)} Archivdateien); alter Stand beiseitegelegt "
        f"(pre_restore_{timestamp})"
    )

    return {"database": True, "archive_files": len(archive_members)}


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
    )

    # Die Migration ist prozessweit einmalig — nach dem Austausch der DB muss
    # sie erneut laufen (die wiederhergestellte DB kann älter sein).
    import src.database.database as database

    database._schema_ready = False

    return result

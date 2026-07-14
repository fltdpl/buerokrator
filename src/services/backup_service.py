"""Backup: Datenbank + Archivordner als eine ZIP-Datei sichern.

Framework-neutral und offline — schreibt nur an einen lokalen Zielort. Der
reine `create_backup` ist ohne App-Kontext testbar; `run_backup` verdrahtet
ihn mit der Konfiguration.
"""

import os
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

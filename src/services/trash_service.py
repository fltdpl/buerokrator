"""Papierkorb: Inhalt auflisten, wiederherstellen, leeren.

Wiederherstellen legt die Datei zurück in die Inbox, nicht ins Archiv: der
DB-Eintrag ist beim Löschen verschwunden, das Dokument muss also erneut durch
den Import (klassifizieren, benennen, archivieren). Das ist der einzige Weg,
der wieder einen konsistenten Zustand herstellt.
"""

from datetime import datetime
from pathlib import Path

from src.core.config import load_config
from src.organizer.filename_builder import get_unique_target_path
from src.organizer.trash import get_trash_dir


def _inbox_path():
    return Path(load_config()["paths"]["inbox"])


def list_trash(trash_dir=None):
    """Dateien im Papierkorb (neueste zuerst) als Plain Data."""
    trash = Path(trash_dir) if trash_dir is not None else get_trash_dir()

    if not trash.exists():
        return []

    entries = []
    for path in trash.iterdir():
        if not path.is_file():
            continue

        stat = path.stat()
        entries.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "deleted_at": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%d.%m.%Y %H:%M"
                ),
                "deleted_timestamp": stat.st_mtime,
            }
        )

    return sorted(entries, key=lambda entry: entry["deleted_timestamp"], reverse=True)


def restore_from_trash(name, trash_dir=None, inbox_dir=None):
    """Verschiebt eine Datei zurück in die Inbox; None, wenn sie fehlt.

    Der Name wird auf den Dateianteil reduziert — ein Pfad von außen darf
    nicht aus dem Papierkorb herausführen.
    """
    trash = Path(trash_dir) if trash_dir is not None else get_trash_dir()
    source = trash / Path(name).name

    if not source.is_file():
        return None

    inbox = Path(inbox_dir) if inbox_dir else _inbox_path()
    inbox.mkdir(parents=True, exist_ok=True)
    target = get_unique_target_path(inbox / source.name)
    source.rename(target)

    return target


def empty_trash(trash_dir=None):
    """Löscht den Papierkorb-Inhalt endgültig; liefert die Anzahl der Dateien.

    Der einzige Ort im Projekt, an dem Dokumentdateien wirklich verschwinden —
    und er wird ausschließlich durch eine ausdrückliche Nutzeraktion erreicht.
    """
    trash = Path(trash_dir) if trash_dir is not None else get_trash_dir()

    if not trash.exists():
        return 0

    removed = 0
    for path in trash.iterdir():
        if path.is_file():
            path.unlink()
            removed += 1

    return removed

"""Papierkorb: Inhalt auflisten, wiederherstellen, leeren.

Wiederherstellen legt die Datei zurück in die Inbox, nicht ins Archiv: der
DB-Eintrag ist beim Löschen verschwunden, das Dokument muss also erneut durch
den Import (klassifizieren, benennen, archivieren). Das ist der einzige Weg,
der wieder einen konsistenten Zustand herstellt.

Zu jeder Datei kann eine HERKUNFT notiert sein. Der Papierkorb liest sonst nur
das Dateisystem, und dort steht nicht, warum etwas hier liegt: eine beim
Import abgewiesene Dublette sah aus wie ein von Hand gelöschtes Dokument, der
Grund stand allein im Log. Die Notiz trägt nur die Dokument-ID — ein Name
ändert sich beim Umbenennen, die ID nicht.
"""

from datetime import datetime
from pathlib import Path

from src.core.config import load_config
from src.organizer.filename_builder import get_unique_target_path
from src.organizer.trash import (
    HERKUNFT_DATEI,
    get_trash_dir,
    lies_herkunft,
    vergiss_herkunft,
)


def _inbox_path():
    return Path(load_config()["paths"]["inbox"])


def list_trash(trash_dir=None):
    """Dateien im Papierkorb (neueste zuerst) als Plain Data."""
    trash = Path(trash_dir) if trash_dir is not None else get_trash_dir()

    if not trash.exists():
        return []

    herkunft = lies_herkunft(trash)
    entries = []
    for path in trash.iterdir():
        if not path.is_file() or path.name == HERKUNFT_DATEI:
            continue

        stat = path.stat()
        entries.append(
            {
                "name": path.name,
                "herkunft": herkunft.get(path.name),
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

    # Die Notiz muss mit: der Name wird im Papierkorb wieder frei, und sie
    # hinge sonst an der nächsten Datei, die so heißt.
    vergiss_herkunft(source.name, trash_dir=trash)

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
        if not path.is_file():
            continue

        # Die Notizdatei geht mit, zählt aber nicht: gemeldet wird, wie viele
        # DOKUMENTE verschwunden sind.
        zaehlt = path.name != HERKUNFT_DATEI
        path.unlink()
        removed += 1 if zaehlt else 0

    return removed

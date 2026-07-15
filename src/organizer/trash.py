"""Papierkorb: Dateien verschieben statt löschen.

Auf Archivdateien wird nie `unlink` aufgerufen — ein Fehlklick (oder eine
falsch erkannte Dublette) darf kein Original vernichten.
"""

from pathlib import Path
import shutil

from src.core.app_home import get_app_home
from src.organizer.filename_builder import get_unique_target_path


def get_trash_dir() -> Path:
    """Papierkorb-Ordner im App-Home (pro Aufruf aufgelöst, testfreundlich)."""
    return get_app_home() / "trash"


def move_to_trash(source, trash_dir=None):
    """Verschiebt die Datei in den Papierkorb; None, wenn sie nicht existiert.

    Namenskollisionen werden über get_unique_target_path aufgelöst, damit der
    Papierkorb nichts überschreibt, was schon in ihm liegt.
    """
    source = Path(source)

    if not source.exists():
        return None

    trash = Path(trash_dir) if trash_dir is not None else get_trash_dir()
    trash.mkdir(parents=True, exist_ok=True)
    target = get_unique_target_path(trash / source.name)
    shutil.move(str(source), str(target))

    return target

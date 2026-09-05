"""Papierkorb: Dateien verschieben statt löschen.

Auf Archivdateien wird nie `unlink` aufgerufen — ein Fehlklick (oder eine
falsch erkannte Dublette) darf kein Original vernichten.
"""

from pathlib import Path
import json
import os
import shutil

from src.core.app_home import get_app_home
from src.organizer.filename_builder import get_unique_target_path


def get_trash_dir() -> Path:
    """Papierkorb-Ordner im App-Home (pro Aufruf aufgelöst, testfreundlich)."""
    return get_app_home() / "trash"


# Versteckt und aus jeder Auflistung gefiltert: die Buchhaltung des
# Papierkorbs darf nicht als sein Inhalt erscheinen.
HERKUNFT_DATEI = ".herkunft.json"


def _herkunft_pfad(trash):
    return Path(trash) / HERKUNFT_DATEI


def lies_herkunft(trash_dir=None):
    """Notizen als {dateiname: {"grund", "dokument_id"}} — leer, wenn keine da."""
    trash = Path(trash_dir) if trash_dir is not None else get_trash_dir()
    pfad = _herkunft_pfad(trash)

    if not pfad.is_file():
        return {}

    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))

    except (OSError, ValueError):
        # Eine unlesbare Notiz darf den Papierkorb nicht unbenutzbar machen —
        # sie ist Auskunft, nicht Bestand.
        return {}

    return daten if isinstance(daten, dict) else {}


def _schreib_herkunft(trash, daten):
    pfad = _herkunft_pfad(trash)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
    # Sie trägt Dateinamen aus dem Bestand — dieselbe Stufe wie Log und DB.
    os.chmod(pfad, 0o600)


def notiere_herkunft(dateiname, dokument_id, trash_dir=None):
    """Hält fest, dass `dateiname` als Dublette von `dokument_id` hier landete.

    `dateiname` muss der TATSÄCHLICHE Name im Papierkorb sein (den liefert
    `move_to_trash`), nicht der aus der Inbox: bei einer Namenskollision weicht
    der Papierkorb aus, und die Notiz hinge sonst an der falschen Datei.
    """
    trash = Path(trash_dir) if trash_dir is not None else get_trash_dir()
    daten = lies_herkunft(trash)
    daten[Path(dateiname).name] = {"grund": "dublette", "dokument_id": dokument_id}
    _schreib_herkunft(trash, daten)


def vergiss_herkunft(dateiname, trash_dir=None):
    """Entfernt die Notiz — der Name wird im Papierkorb wieder frei."""
    trash = Path(trash_dir) if trash_dir is not None else get_trash_dir()
    daten = lies_herkunft(trash)

    if daten.pop(Path(dateiname).name, None) is not None:
        _schreib_herkunft(trash, daten)


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

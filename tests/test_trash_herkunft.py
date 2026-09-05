"""Warum liegt diese Datei im Papierkorb?

Beim Import wird eine byte-gleiche Datei automatisch dorthin verschoben —
richtig, aber unsichtbar: der Papierkorb las bisher nur das Dateisystem und
zeigte Name, Groesse, Datum. Eine abgewiesene Dublette sah dort aus wie ein
von Hand geloeschtes Dokument, und der Grund stand allein im Log.

Die Herkunft haelt deshalb eine Notiz neben den Dateien fest. Sie traegt nur
die Dokument-ID, nicht den Namen: der Name kann sich durch Umbenennen
aendern, die ID nicht.

Alle Werte erfunden.
"""

import os
import stat

from src.organizer.trash import move_to_trash, notiere_herkunft
from src.services.trash_service import empty_trash, list_trash, restore_from_trash


def _file(directory, name, content="x"):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def test_notierte_herkunft_erscheint_in_der_liste(tmp_path):
    trash = tmp_path / "trash"
    _file(trash, "rechnung.pdf")

    notiere_herkunft("rechnung.pdf", dokument_id=625, trash_dir=trash)
    eintrag = list_trash(trash_dir=trash)[0]

    assert eintrag["herkunft"]["dokument_id"] == 625


def test_ohne_notiz_bleibt_die_herkunft_leer(tmp_path):
    """Von Hand geloeschte Dokumente tragen keine — das Feld muss trotzdem da
    sein, damit die Anzeige nicht auf ein fehlendes Feld laeuft."""
    trash = tmp_path / "trash"
    _file(trash, "rechnung.pdf")

    assert list_trash(trash_dir=trash)[0]["herkunft"] is None


def test_die_notizdatei_ist_kein_papierkorb_eintrag(tmp_path):
    """Sonst stuende die Buchhaltung des Papierkorbs in ihm selbst."""
    trash = tmp_path / "trash"
    _file(trash, "rechnung.pdf")
    notiere_herkunft("rechnung.pdf", dokument_id=625, trash_dir=trash)

    namen = [eintrag["name"] for eintrag in list_trash(trash_dir=trash)]

    assert namen == ["rechnung.pdf"]


def test_notiz_folgt_dem_eindeutigen_namen(tmp_path):
    """`move_to_trash` weicht bei Namenskollision aus — die Notiz muss auf den
    TATSAECHLICHEN Namen im Papierkorb zeigen, sonst haengt sie an der
    falschen Datei."""
    trash = tmp_path / "trash"
    erste = move_to_trash(_file(tmp_path / "a", "rechnung.pdf", "alt"), trash_dir=trash)
    zweite = move_to_trash(_file(tmp_path / "b", "rechnung.pdf", "neu"), trash_dir=trash)

    assert erste.name != zweite.name

    notiere_herkunft(zweite.name, dokument_id=625, trash_dir=trash)
    nach_name = {e["name"]: e["herkunft"] for e in list_trash(trash_dir=trash)}

    assert nach_name[zweite.name]["dokument_id"] == 625
    assert nach_name[erste.name] is None


def test_wiederherstellen_raeumt_die_notiz_mit_weg(tmp_path):
    """Sonst haengt sie an einem Namen, den der naechste Import wiederverwendet."""
    trash = tmp_path / "trash"
    _file(trash, "rechnung.pdf")
    notiere_herkunft("rechnung.pdf", dokument_id=625, trash_dir=trash)

    restore_from_trash("rechnung.pdf", trash_dir=trash, inbox_dir=tmp_path / "inbox")

    _file(trash, "rechnung.pdf")
    assert list_trash(trash_dir=trash)[0]["herkunft"] is None


def test_leeren_zaehlt_die_notizdatei_nicht_mit(tmp_path):
    """Die gemeldete Zahl ist die der Dokumente, nicht der Dateien."""
    trash = tmp_path / "trash"
    _file(trash, "a.pdf")
    _file(trash, "b.pdf")
    notiere_herkunft("a.pdf", dokument_id=625, trash_dir=trash)

    assert empty_trash(trash_dir=trash) == 2
    assert list_trash(trash_dir=trash) == []
    assert not any(pfad.is_file() for pfad in trash.iterdir())


def test_notizdatei_gehoert_nur_dem_besitzer(tmp_path):
    """Sie traegt Dateinamen aus dem Bestand — dieselbe Stufe wie Log und DB."""
    trash = tmp_path / "trash"
    _file(trash, "rechnung.pdf")
    notiere_herkunft("rechnung.pdf", dokument_id=625, trash_dir=trash)

    notiz = next(p for p in trash.iterdir() if p.name.startswith("."))

    assert stat.S_IMODE(os.stat(notiz).st_mode) == 0o600

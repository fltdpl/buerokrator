"""Papierkorb: auflisten, wiederherstellen, leeren."""

from src.organizer.trash import move_to_trash
from src.services.trash_service import empty_trash, list_trash, restore_from_trash


def _file(directory, name, content="x"):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def test_move_to_trash_verschiebt_statt_zu_loeschen(tmp_path):
    source = _file(tmp_path / "archive", "rechnung.pdf")
    trash = tmp_path / "trash"

    target = move_to_trash(source, trash_dir=trash)

    assert not source.exists()
    assert target.read_text(encoding="utf-8") == "x"


def test_gleichnamige_dateien_ueberschreiben_sich_nicht(tmp_path):
    trash = tmp_path / "trash"
    move_to_trash(_file(tmp_path / "a", "rechnung.pdf", "erste"), trash_dir=trash)
    move_to_trash(_file(tmp_path / "b", "rechnung.pdf", "zweite"), trash_dir=trash)

    contents = sorted(path.read_text(encoding="utf-8") for path in trash.iterdir())

    assert contents == ["erste", "zweite"]


def test_move_to_trash_ohne_datei_liefert_none(tmp_path):
    assert move_to_trash(tmp_path / "weg.pdf", trash_dir=tmp_path / "trash") is None


def test_list_trash_ist_leer_ohne_ordner(tmp_path):
    assert list_trash(trash_dir=tmp_path / "trash") == []


def test_list_trash_listet_dateien(tmp_path):
    trash = tmp_path / "trash"
    _file(trash, "a.pdf")
    _file(trash, "b.pdf", "laengerer inhalt")

    entries = list_trash(trash_dir=trash)

    assert {entry["name"] for entry in entries} == {"a.pdf", "b.pdf"}
    assert all(entry["size"] > 0 for entry in entries)


def test_restore_legt_die_datei_in_die_inbox(tmp_path):
    trash = tmp_path / "trash"
    _file(trash, "rechnung.pdf", "inhalt")
    inbox = tmp_path / "inbox"

    target = restore_from_trash("rechnung.pdf", trash_dir=trash, inbox_dir=inbox)

    assert target == inbox / "rechnung.pdf"
    assert target.read_text(encoding="utf-8") == "inhalt"
    assert not (trash / "rechnung.pdf").exists()


def test_restore_bricht_nicht_aus_dem_papierkorb_aus(tmp_path):
    # Ein Pfadanteil im Namen darf nicht dazu führen, dass eine Datei
    # außerhalb des Papierkorbs angefasst wird.
    trash = tmp_path / "trash"
    trash.mkdir()
    outside = _file(tmp_path / "geheim", "passwoerter.pdf")

    assert (
        restore_from_trash(
            "../geheim/passwoerter.pdf", trash_dir=trash, inbox_dir=tmp_path / "inbox"
        )
        is None
    )
    assert outside.exists()


def test_restore_einer_fehlenden_datei_liefert_none(tmp_path):
    trash = tmp_path / "trash"
    trash.mkdir()

    assert restore_from_trash("weg.pdf", trash_dir=trash, inbox_dir=tmp_path) is None


def test_empty_trash_loescht_alles_und_zaehlt(tmp_path):
    trash = tmp_path / "trash"
    _file(trash, "a.pdf")
    _file(trash, "b.pdf")

    assert empty_trash(trash_dir=trash) == 2
    assert list_trash(trash_dir=trash) == []

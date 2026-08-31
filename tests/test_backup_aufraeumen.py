"""Aufräumen rund um die Sicherungen.

Jede Sicherung ist eine Vollkopie, und jede Wiederherstellung legt den
bisherigen Stand daneben statt ihn zu löschen. Beides ist richtig — aber
niemand räumt es je weg, und der Platzbedarf wächst deshalb unbegrenzt.

Gelöscht wird trotzdem nichts: die Kandidaten wandern in einen eigenen
Papierkorb für Sicherungen. Bewusst NICHT in den Dokument-Papierkorb — der
bietet seinen Inhalt zum Wiederherstellen in die Inbox an, und eine
Backup-ZIP dort wäre ein Dokument, das importiert werden will.
"""

import zipfile

from src.services.backup_service import (
    aufraeum_kandidaten,
    in_papierkorb,
    leere_papierkorb,
    papierkorb_inhalt,
)


def _sicherung(ordner, zeitpunkt, groesse=100):
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / f"buerokrator_backup_{zeitpunkt}.zip"

    with zipfile.ZipFile(pfad, "w") as archive:
        archive.writestr("database/buerokrator.db", "x" * groesse)

    return pfad


def _bestand(tmp_path):
    """Ein Profil mit aktiver DB, aktivem Archiv und aktiver Konfiguration."""
    (tmp_path / "database").mkdir()
    (tmp_path / "database" / "buerokrator.db").write_bytes(b"DB")
    (tmp_path / "archive" / "2024").mkdir(parents=True)
    (tmp_path / "archive" / "2024" / "a.pdf").write_bytes(b"PDF")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "aussteller_aliase.yaml").write_text("x: y\n")

    return {
        "target_dir": tmp_path / "backups",
        "db_path": tmp_path / "database" / "buerokrator.db",
        "archive_dir": tmp_path / "archive",
        "config_dir": tmp_path / "config",
    }


def _namen(kandidaten):
    return sorted(eintrag["name"] for eintrag in kandidaten)


# ------------------------------------------------------ alte Sicherungen


def test_die_juengsten_bleiben(tmp_path):
    bestand = _bestand(tmp_path)

    for tag in ("20260101_090000", "20260401_090000", "20260701_090000"):
        _sicherung(bestand["target_dir"], tag)

    assert aufraeum_kandidaten(**bestand, behalten=3) == []


def test_aeltere_jenseits_der_grenze_sind_kandidaten(tmp_path):
    bestand = _bestand(tmp_path)

    for tag in (
        "20250101_090000",
        "20250401_090000",
        "20260101_090000",
        "20260401_090000",
        "20260701_090000",
    ):
        _sicherung(bestand["target_dir"], tag)

    kandidaten = aufraeum_kandidaten(**bestand, behalten=3)

    assert _namen(kandidaten) == [
        "buerokrator_backup_20250101_090000.zip",
        "buerokrator_backup_20250401_090000.zip",
    ]
    assert {eintrag["art"] for eintrag in kandidaten} == {"sicherung"}


def test_alter_allein_macht_keinen_kandidaten(tmp_path):
    """Wer selten sichert, hat nur alte Sicherungen — sie sind trotzdem
    alles, was er hat."""
    bestand = _bestand(tmp_path)
    _sicherung(bestand["target_dir"], "20200101_090000")

    assert aufraeum_kandidaten(**bestand, behalten=3) == []


def test_unvollstaendige_datei_ist_immer_ein_kandidat(tmp_path):
    """Sie ist per Definition wertlos und zählt nicht als Sicherung."""
    bestand = _bestand(tmp_path)
    bestand["target_dir"].mkdir()
    (bestand["target_dir"] / "b.zip.unvollstaendig").write_bytes(b"halb")

    kandidaten = aufraeum_kandidaten(**bestand, behalten=3)

    assert _namen(kandidaten) == ["b.zip.unvollstaendig"]


# ------------------------------------------- Reste frueherer Wiederherstellungen


def test_reste_der_wiederherstellung_sind_kandidaten(tmp_path):
    bestand = _bestand(tmp_path)

    (tmp_path / "database" / "pre_restore_20260101_120000.db").write_bytes(b"alt")
    (tmp_path / "database" / "pre_restore_20260101_120000.db-wal").write_bytes(b"w")
    (tmp_path / "archive_vor_wiederherstellung_20260101_120000" / "2023").mkdir(
        parents=True
    )
    (
        tmp_path
        / "archive_vor_wiederherstellung_20260101_120000"
        / "2023"
        / "alt.pdf"
    ).write_bytes(b"PDF")
    (tmp_path / "config_vor_wiederherstellung_20260101_120000").mkdir()

    kandidaten = aufraeum_kandidaten(**bestand, behalten=3)

    assert _namen(kandidaten) == [
        "archive_vor_wiederherstellung_20260101_120000",
        "config_vor_wiederherstellung_20260101_120000",
        "pre_restore_20260101_120000.db",
        "pre_restore_20260101_120000.db-wal",
    ]
    assert {eintrag["art"] for eintrag in kandidaten} == {"rest"}


def test_ordnergroesse_zaehlt_den_ganzen_baum(tmp_path):
    bestand = _bestand(tmp_path)
    rest = tmp_path / "archive_vor_wiederherstellung_20260101_120000" / "2023"
    rest.mkdir(parents=True)
    (rest / "a.pdf").write_bytes(b"x" * 700)
    (rest / "b.pdf").write_bytes(b"x" * 300)

    kandidat = aufraeum_kandidaten(**bestand, behalten=3)[0]

    assert kandidat["groesse"] == 1000


def test_der_lebende_bestand_ist_niemals_kandidat(tmp_path):
    """Der teuerste denkbare Fehler dieser Funktion."""
    bestand = _bestand(tmp_path)

    for tag in ("20250101_090000", "20260701_090000"):
        _sicherung(bestand["target_dir"], tag)

    (tmp_path / "database" / "pre_restore_20260101_120000.db").write_bytes(b"alt")

    pfade = {eintrag["pfad"] for eintrag in aufraeum_kandidaten(**bestand, behalten=1)}

    assert str(bestand["db_path"]) not in pfade
    assert str(bestand["archive_dir"]) not in pfade
    assert str(bestand["config_dir"]) not in pfade
    assert bestand["db_path"].exists()
    assert (bestand["archive_dir"] / "2024" / "a.pdf").exists()


# ------------------------------------------------------------- Papierkorb


def test_kandidaten_wandern_in_den_papierkorb(tmp_path):
    bestand = _bestand(tmp_path)
    alt = _sicherung(bestand["target_dir"], "20250101_090000")
    _sicherung(bestand["target_dir"], "20260701_090000")

    papierkorb = tmp_path / "trash" / "sicherungen"
    ergebnis = in_papierkorb(
        aufraeum_kandidaten(**bestand, behalten=1), papierkorb
    )

    assert ergebnis["anzahl"] == 1
    assert not alt.exists()
    assert (papierkorb / alt.name).exists()


def test_ganze_ordner_wandern_mit_inhalt(tmp_path):
    bestand = _bestand(tmp_path)
    rest = tmp_path / "archive_vor_wiederherstellung_20260101_120000" / "2023"
    rest.mkdir(parents=True)
    (rest / "alt.pdf").write_bytes(b"PDF")

    papierkorb = tmp_path / "trash" / "sicherungen"
    in_papierkorb(aufraeum_kandidaten(**bestand, behalten=3), papierkorb)

    ziel = papierkorb / "archive_vor_wiederherstellung_20260101_120000"

    assert (ziel / "2023" / "alt.pdf").read_bytes() == b"PDF"


def test_papierkorb_ueberschreibt_nichts(tmp_path):
    bestand = _bestand(tmp_path)
    papierkorb = tmp_path / "trash" / "sicherungen"
    papierkorb.mkdir(parents=True)
    (papierkorb / "buerokrator_backup_20250101_090000.zip").write_bytes(b"schon da")

    _sicherung(bestand["target_dir"], "20250101_090000")
    _sicherung(bestand["target_dir"], "20260701_090000")

    in_papierkorb(aufraeum_kandidaten(**bestand, behalten=1), papierkorb)

    assert (papierkorb / "buerokrator_backup_20250101_090000.zip").read_bytes() == (
        b"schon da"
    )
    assert len(list(papierkorb.iterdir())) == 2


def test_papierkorb_meldet_seinen_inhalt(tmp_path):
    papierkorb = tmp_path / "trash" / "sicherungen"

    assert papierkorb_inhalt(papierkorb) == {"anzahl": 0, "bytes": 0}

    papierkorb.mkdir(parents=True)
    (papierkorb / "alt.zip").write_bytes(b"x" * 500)
    (papierkorb / "ordner").mkdir()
    (papierkorb / "ordner" / "a.pdf").write_bytes(b"x" * 500)

    assert papierkorb_inhalt(papierkorb) == {"anzahl": 2, "bytes": 1000}


def test_leeren_loescht_endgueltig(tmp_path):
    papierkorb = tmp_path / "trash" / "sicherungen"
    papierkorb.mkdir(parents=True)
    (papierkorb / "alt.zip").write_bytes(b"x" * 500)
    (papierkorb / "ordner" / "tief").mkdir(parents=True)
    (papierkorb / "ordner" / "tief" / "a.pdf").write_bytes(b"x" * 500)

    ergebnis = leere_papierkorb(papierkorb)

    assert ergebnis == {"anzahl": 2, "bytes": 1000}
    assert list(papierkorb.iterdir()) == []


def test_leeren_ohne_papierkorb_ist_kein_fehler(tmp_path):
    assert leere_papierkorb(tmp_path / "gibt_es_nicht") == {"anzahl": 0, "bytes": 0}


def test_der_dokument_papierkorb_bleibt_unberuehrt(tmp_path):
    """Eine Backup-ZIP im Dokument-Papierkorb böte sich zum Import an."""
    from src.services.trash_service import list_trash

    bestand = _bestand(tmp_path)
    _sicherung(bestand["target_dir"], "20250101_090000")
    _sicherung(bestand["target_dir"], "20260701_090000")

    trash = tmp_path / "trash"
    in_papierkorb(aufraeum_kandidaten(**bestand, behalten=1), trash / "sicherungen")

    assert list_trash(trash) == []

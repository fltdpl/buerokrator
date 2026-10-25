"""Die Test-Wache in conftest.py muss Schreibzugriffe TIEF im Bestand sehen.

Die erste Fassung verglich nur die mtime der obersten Ordner. Ein
Schreibzugriff in `profiles/1/database/` ändert aber nur die mtime des
tieferen Ordners — ein Test, der die echte Datenbank beschrieb, lief durch.
Geprüft wird hier an einem Nachbau in tmp_path, nie am echten Bestand.
"""

import os

from tests.conftest import _signatur


def _bestand(wurzel):
    datenbank = wurzel / "profiles" / "1" / "database"
    datenbank.mkdir(parents=True)
    (datenbank / "buerokrator.db").write_bytes(b"alt")
    archiv = wurzel / "profiles" / "1" / "archive" / "2024" / "Wohnen"
    archiv.mkdir(parents=True)
    (archiv / "beleg.pdf").write_bytes(b"%PDF")

    return (wurzel / "profiles.yaml", wurzel / "profiles")


def _spaeter(pfad):
    """mtime sicher verschieben — manche Dateisysteme lösen grob auf."""
    stand = pfad.stat()
    os.utime(pfad, ns=(stand.st_atime_ns, stand.st_mtime_ns + 10_000_000))


def test_ueberschreiben_einer_tiefen_datei_faellt_auf(tmp_path):
    wache = _bestand(tmp_path)
    vorher = _signatur(wache)

    datei = tmp_path / "profiles" / "1" / "database" / "buerokrator.db"
    datei.write_bytes(b"neu")
    _spaeter(datei)

    assert _signatur(wache) != vorher


def test_neue_datei_tief_im_archiv_faellt_auf(tmp_path):
    wache = _bestand(tmp_path)
    vorher = _signatur(wache)

    (tmp_path / "profiles" / "1" / "archive" / "2024" / "Wohnen" / "neu.pdf").write_bytes(b"x")

    assert _signatur(wache) != vorher


def test_geloeschte_datei_faellt_auf(tmp_path):
    wache = _bestand(tmp_path)
    vorher = _signatur(wache)

    (tmp_path / "profiles" / "1" / "archive" / "2024" / "Wohnen" / "beleg.pdf").unlink()

    assert _signatur(wache) != vorher


def test_oberster_ordner_bleibt_dabei_unveraendert(tmp_path):
    # Belegt die Lücke der ersten Fassung: genau das sah sie nicht.
    _bestand(tmp_path)
    oben = (tmp_path / "profiles").stat().st_mtime_ns

    (tmp_path / "profiles" / "1" / "database" / "buerokrator.db").write_bytes(b"neu")

    assert (tmp_path / "profiles").stat().st_mtime_ns == oben


def test_ohne_aenderung_bleibt_die_signatur_gleich(tmp_path):
    wache = _bestand(tmp_path)

    assert _signatur(wache) == _signatur(wache)


def test_fehlende_pfade_sind_kein_fehler(tmp_path):
    wache = (tmp_path / "gibt-es-nicht.yaml", tmp_path / "auch-nicht")

    assert _signatur(wache) == _signatur(wache)

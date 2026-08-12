"""Archivpfade wieder an das aktuelle Archiv binden.

Anlass ist ein realer Fehlerfall: nach dem Wiederherstellen einer Sicherung
an einem ANDEREN Ort (frische Installation) zeigten alle Altdokumente ins
Leere — die Dateien lagen im Archiv, aber `archive_path` trug noch den
absoluten Pfad von der Sicherungszeit. Die Detailansicht meldete
"PDF-Datei nicht gefunden", während alle Datenbankwerte richtig aussahen.
"""

import sqlite3

import pytest

from src.services.archive_repair import pruefe_archivpfade, repariere_archivpfade


def _datenbank(path, pfade):
    """Minimale documents-Tabelle mit vorgegebenen archive_path-Werten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE documents (id INTEGER PRIMARY KEY, archive_path TEXT)"
    )
    conn.executemany(
        "INSERT INTO documents (archive_path) VALUES (?)", [(p,) for p in pfade]
    )
    conn.commit()
    conn.close()

    return path


def _pfade(db):
    conn = sqlite3.connect(db)

    try:
        return [row[0] for row in conn.execute("SELECT archive_path FROM documents")]

    finally:
        conn.close()


def _lege_ab(archiv, jahr, kategorie, name):
    ziel = archiv / jahr / kategorie / name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(b"PDF")

    return ziel


def test_bindet_absoluten_pfad_vom_alten_ort_neu(tmp_path):
    """Der Produktivfall: Pfad zeigt auf ein Archiv, das es nicht mehr gibt."""
    archiv = tmp_path / "profiles" / "1" / "archive"
    _lege_ab(archiv, "2024", "Wohnen", "miete.pdf")

    db = _datenbank(
        tmp_path / "database" / "test.db",
        ["/woanders/buerokrator/archive/2024/Wohnen/miete.pdf"],
    )

    bericht = repariere_archivpfade(db, archiv, basis=tmp_path)

    assert bericht["repariert"] == 1
    assert bericht["ungeloest"] == 0
    assert _pfade(db) == [str(archiv / "2024" / "Wohnen" / "miete.pdf")]


def test_macht_relativen_pfad_absolut(tmp_path):
    """Ältere Importe hinterließen relative Pfade — sie lösen gegen die cwd auf."""
    archiv = tmp_path / "archive"
    _lege_ab(archiv, "2025", "Rechnungen", "strom.pdf")

    db = _datenbank(
        tmp_path / "database" / "test.db", ["archive/2025/Rechnungen/strom.pdf"]
    )

    bericht = repariere_archivpfade(db, archiv, basis=tmp_path)

    assert bericht["repariert"] == 1
    assert _pfade(db) == [str(archiv / "2025" / "Rechnungen" / "strom.pdf")]


def test_laesst_heile_pfade_unberuehrt(tmp_path):
    archiv = tmp_path / "archive"
    datei = _lege_ab(archiv, "2024", "Wohnen", "miete.pdf")

    db = _datenbank(tmp_path / "database" / "test.db", [str(datei)])

    bericht = repariere_archivpfade(db, archiv, basis=tmp_path)

    assert bericht["in_ordnung"] == 1
    assert bericht["repariert"] == 0
    assert _pfade(db) == [str(datei)]


def test_meldet_ungeloeste_ohne_etwas_zu_aendern(tmp_path):
    """Fehlt die Datei auch im aktuellen Archiv, wird NICHTS geschrieben.

    Ein geratener Pfad wäre schlimmer als der alte: die Zeile sähe heil aus
    und zeigte doch ins Leere.
    """
    archiv = tmp_path / "archive"
    archiv.mkdir()

    db = _datenbank(
        tmp_path / "database" / "test.db", ["/alt/archive/2024/Wohnen/weg.pdf"]
    )

    bericht = repariere_archivpfade(db, archiv, basis=tmp_path)

    assert bericht["ungeloest"] == 1
    assert bericht["ungeloeste_ids"] == [1]
    assert _pfade(db) == ["/alt/archive/2024/Wohnen/weg.pdf"]


def test_pruefung_aendert_nichts(tmp_path):
    """Der Trockenlauf meldet dieselben Zahlen, schreibt aber nicht."""
    archiv = tmp_path / "archive"
    _lege_ab(archiv, "2024", "Wohnen", "miete.pdf")

    alt = "/alt/archive/2024/Wohnen/miete.pdf"
    db = _datenbank(tmp_path / "database" / "test.db", [alt])

    bericht = pruefe_archivpfade(db, archiv, basis=tmp_path)

    assert bericht["reparierbar"] == 1
    assert _pfade(db) == [alt]


def test_sichert_die_datenbank_vor_dem_schreiben(tmp_path):
    archiv = tmp_path / "archive"
    _lege_ab(archiv, "2024", "Wohnen", "miete.pdf")

    db = _datenbank(
        tmp_path / "database" / "test.db", ["/alt/archive/2024/Wohnen/miete.pdf"]
    )

    repariere_archivpfade(db, archiv, basis=tmp_path)

    sicherungen = list(db.parent.glob("pre_pfadreparatur_*.db"))

    assert len(sicherungen) == 1
    assert _pfade(sicherungen[0]) == ["/alt/archive/2024/Wohnen/miete.pdf"]


def test_ohne_reparaturbedarf_keine_sicherung(tmp_path):
    archiv = tmp_path / "archive"
    datei = _lege_ab(archiv, "2024", "Wohnen", "miete.pdf")

    db = _datenbank(tmp_path / "database" / "test.db", [str(datei)])

    repariere_archivpfade(db, archiv, basis=tmp_path)

    assert list(db.parent.glob("pre_pfadreparatur_*.db")) == []


def test_leerer_pfad_bleibt_leer(tmp_path):
    archiv = tmp_path / "archive"
    archiv.mkdir()

    db = _datenbank(tmp_path / "database" / "test.db", [None, ""])

    bericht = repariere_archivpfade(db, archiv, basis=tmp_path)

    assert bericht["ohne_pfad"] == 2
    assert bericht["repariert"] == 0


def test_kein_ausbruch_aus_dem_archiv(tmp_path):
    """Ein Pfad mit .. darf keine Datei außerhalb des Archivs binden."""
    archiv = tmp_path / "archive"
    archiv.mkdir()
    geheim = tmp_path / "geheim.pdf"
    geheim.write_bytes(b"PDF")

    db = _datenbank(tmp_path / "database" / "test.db", ["/alt/archive/../../geheim.pdf"])

    bericht = repariere_archivpfade(db, archiv, basis=tmp_path)

    assert bericht["ungeloest"] == 1
    assert _pfade(db) == ["/alt/archive/../../geheim.pdf"]


def test_zwei_dokumente_binden_nie_dieselbe_datei(tmp_path):
    """Kollisionen wären ein stiller Datenverlust — lieber ungelöst melden."""
    archiv = tmp_path / "archive"
    _lege_ab(archiv, "2024", "Wohnen", "miete.pdf")

    db = _datenbank(
        tmp_path / "database" / "test.db",
        [
            "/alt/archive/2024/Wohnen/miete.pdf",
            "/ganz_anders/archive/2024/Wohnen/miete.pdf",
        ],
    )

    bericht = repariere_archivpfade(db, archiv, basis=tmp_path)

    assert bericht["repariert"] == 0
    assert bericht["kollisionen"] == 2
    assert _pfade(db) == [
        "/alt/archive/2024/Wohnen/miete.pdf",
        "/ganz_anders/archive/2024/Wohnen/miete.pdf",
    ]


def test_fehlende_tabelle_ist_kein_absturz(tmp_path):
    leer = tmp_path / "leer.db"
    sqlite3.connect(leer).close()

    with pytest.raises(RuntimeError, match="documents"):
        repariere_archivpfade(leer, tmp_path / "archive", basis=tmp_path)

"""Datenschutzprüfung am fertigen Release-Paket.

Release-Pakete bündeln `src/classifier/prompts/*` mit — ein Echtname dort
landet in JEDEM veröffentlichten Binary (so geschehen in 0.1.0 und 0.2.0).
`tests/test_keine_echtdaten.py` prüft nur den Quellstand und kann das nicht
sehen.

Die Prüfung lief für 0.3.1 von Hand; das Skript lag im Job-Verzeichnis und
war damit vergänglich. Hier ist sie ein Werkzeug — und damit selbst prüfbar.

**Die Maskierung ist der Teil, der getestet gehört.** Beim Handlauf war das
Ziffernmuster in einem f-string doppelt escaped, sodass eine echte
Rechnungsnummer im Klartext in der Ausgabe landete. Ein Werkzeug, das
Echtdaten sucht und sie beim Melden preisgibt, ist schlimmer als keines.
"""

import sqlite3
import tarfile
import zipfile
from io import BytesIO
from pathlib import Path

from tools.scan_tarball import (
    bericht_zeilen,
    main,
    maskiere,
    pruefe_tarball,
    sammle_bestandswerte,
)


def _bestand(pfad, zeilen):
    """Minimale documents-Tabelle mit vorgegebenen Feldwerten."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(pfad)
    conn.execute(
        "CREATE TABLE documents (id INTEGER PRIMARY KEY, filename TEXT, "
        "extracted_data TEXT)"
    )
    conn.executemany(
        "INSERT INTO documents (filename, extracted_data) VALUES (?, ?)", zeilen
    )
    conn.commit()
    conn.close()

    return pfad


def _paket(pfad, dateien):
    """Tarball aus {name: bytes} — wie ein Release-Paket aufgebaut."""
    pfad.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(pfad, "w:gz") as tf:
        for name, inhalt in dateien.items():
            info = tarfile.TarInfo(name)
            info.size = len(inhalt)
            tf.addfile(info, BytesIO(inhalt))

    return pfad


# ------------------------------------------------------------ Maskierung


def test_maskierung_laesst_weder_ziffer_noch_buchstabe_stehen():
    """Der Fehler aus dem Handlauf: das Ziffernmuster griff nicht.

    Geprüft wird die genaue Eigenschaft: die einzigen alphanumerischen
    Zeichen, die übrig bleiben dürfen, sind die Maskenzeichen selbst.
    """
    original = "Musterfirma GmbH RE-4711 Köln"
    maskiert = maskiere(original)

    assert all(zeichen in "xN" for zeichen in maskiert if zeichen.isalnum())
    assert "Muster" not in maskiert
    assert "4711" not in maskiert
    # Die FORM bleibt erhalten — daran erkennt der Nutzer den Wert wieder.
    assert len(maskiert) == len(original)
    assert maskiert.count(" ") == original.count(" ")


def test_maskierung_faellt_nicht_auf_umlaute_herein():
    """Eine naive `a-z`-Zeichenklasse ließe Umlaute stehen — deutsche
    Ausstellernamen wären damit oft noch zu erraten."""
    maskiert = maskiere("Äöü-Musterkasse Straße 7")

    assert all(zeichen in "xN" for zeichen in maskiert if zeichen.isalnum())
    assert not set("ÄÖÜäöüß") & set(maskiert)


# --------------------------------------------------------- Bestandswerte


def test_sammelt_die_heiklen_felder_und_dateinamen(tmp_path):
    db = _bestand(
        tmp_path / "test.db",
        [
            ("2024-05-02_Musterfirma-GmbH_RE-4711.pdf", '{"issuer": "Musterfirma GmbH", "invoice_number": "RE-4711"}'),
            ("kurz.pdf", '{"issuer": "AG"}'),
        ],
    )

    werte = sammle_bestandswerte(db)

    assert "Musterfirma GmbH" in werte
    assert "2024-05-02_Musterfirma-GmbH_RE-4711.pdf" in werte
    # Zu kurze Werte erzeugen nur Fehlalarme.
    assert "AG" not in werte
    assert "kurz.pdf" not in werte
    assert werte["Musterfirma GmbH"]["felder"] == {"issuer"}


def test_zaehlt_wie_viele_dokumente_einen_wert_tragen(tmp_path):
    """Ein Wert in vielen Dokumenten ist eher Gattungsbegriff als Leck."""
    db = _bestand(
        tmp_path / "test.db",
        [
            (f"datei-{i}.pdf", '{"issuer": "Musterversand AG"}') for i in range(3)
        ],
    )

    werte = sammle_bestandswerte(db)

    assert werte["Musterversand AG"]["dokumente"] == 3


def test_liest_die_datenbank_nur_lesend(tmp_path):
    """Der Bestand ist Ground Truth — ein Prüfwerkzeug fasst ihn nie an."""
    db = _bestand(tmp_path / "test.db", [("datei.pdf", '{"issuer": "Musterfirma GmbH"}')])
    vorher = db.stat().st_mtime_ns

    sammle_bestandswerte(db)

    assert db.stat().st_mtime_ns == vorher


# ------------------------------------------------------------ der Scan


def test_findet_wert_in_einer_textdatei(tmp_path):
    db = _bestand(tmp_path / "test.db", [("datei.pdf", '{"issuer": "Musterfirma GmbH"}')])
    paket = _paket(
        tmp_path / "paket.tar.gz",
        {
            "app/_internal/prompts/extract_invoice.txt": "Aussteller wie Musterfirma GmbH".encode(),
            "app/harmlos.txt": b"nichts zu sehen",
        },
    )

    treffer, geprueft, uebersprungen = pruefe_tarball(paket, sammle_bestandswerte(db))

    assert len(treffer) == 1
    assert treffer[0]["fundorte"] == ["app/_internal/prompts/extract_invoice.txt"]
    assert geprueft == 2
    assert uebersprungen == 0


def test_findet_wert_auch_in_einer_binaerdatei(tmp_path):
    """Der blinde Fleck des Handlaufs: er sah nur Dateien nach Endung an.

    Ein Echtname kann genauso in einer kompilierten Datei stehen — geprüft
    wird deshalb roh über die Bytes, ohne Endungsliste.
    """
    db = _bestand(tmp_path / "test.db", [("datei.pdf", '{"issuer": "Musterfirma GmbH"}')])
    paket = _paket(
        tmp_path / "paket.tar.gz",
        {"app/_internal/lib.so": b"\x7fELF\x00\x00Musterfirma GmbH\x00\xff\xfe"},
    )

    treffer, _, _ = pruefe_tarball(paket, sammle_bestandswerte(db))

    assert len(treffer) == 1
    assert treffer[0]["fundorte"] == ["app/_internal/lib.so"]


def test_schaut_in_mitgelieferte_zip_archive(tmp_path):
    """`base_library.zip` liegt im Paket; deflate versteckt den Klartext."""
    db = _bestand(tmp_path / "test.db", [("datei.pdf", '{"issuer": "Musterfirma GmbH"}')])

    puffer = BytesIO()

    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("drin/modul.py", "ISSUER = 'Musterfirma GmbH'\n" * 40)

    paket = _paket(
        tmp_path / "paket.tar.gz",
        {"app/_internal/base_library.zip": puffer.getvalue()},
    )

    treffer, _, _ = pruefe_tarball(paket, sammle_bestandswerte(db))

    assert len(treffer) == 1
    assert "base_library.zip" in treffer[0]["fundorte"][0]


def test_ueberspringt_die_ca_sammlung_und_meldet_das(tmp_path):
    """CA-Namen kollidieren echt mit Ausstellernamen — aber Fremdcode.

    Übersprungen wird gemeldet, nicht verschwiegen: eine stille Ausnahme
    liest sich hinterher wie „alles geprüft".
    """
    db = _bestand(tmp_path / "test.db", [("datei.pdf", '{"issuer": "Musterfirma GmbH"}')])
    paket = _paket(
        tmp_path / "paket.tar.gz",
        {"app/_internal/certifi/cacert.pem": b"CN = Musterfirma GmbH Root CA"},
    )

    treffer, geprueft, uebersprungen = pruefe_tarball(paket, sammle_bestandswerte(db))

    assert treffer == []
    assert geprueft == 0
    assert uebersprungen == 1


# ------------------------------------------------- Bericht und Exitcode


def test_bericht_nennt_niemals_den_klartextwert(tmp_path):
    """Die eigentliche Wache — sie sichert die FORM, nicht die Absicht."""
    db = _bestand(
        tmp_path / "test.db",
        [("datei.pdf", '{"issuer": "Musterfirma GmbH", "invoice_number": "RE-4711"}')],
    )
    paket = _paket(
        tmp_path / "paket.tar.gz",
        {"app/prompt.txt": b"Musterfirma GmbH und RE-4711"},
    )

    treffer, geprueft, uebersprungen = pruefe_tarball(paket, sammle_bestandswerte(db))
    text = "\n".join(bericht_zeilen(treffer, geprueft, uebersprungen))

    assert "Musterfirma GmbH" not in text
    assert "RE-4711" not in text
    # Der Fundort im Paket ist dagegen kein Nutzerdatum und muss dastehen.
    assert "app/prompt.txt" in text


def test_exitcode_meldet_den_befund(tmp_path, capsys):
    db = _bestand(tmp_path / "test.db", [("datei.pdf", '{"issuer": "Musterfirma GmbH"}')])

    sauber = _paket(tmp_path / "sauber.tar.gz", {"app/harmlos.txt": b"nichts"})
    belastet = _paket(tmp_path / "belastet.tar.gz", {"app/p.txt": b"Musterfirma GmbH"})

    assert main(["--db", str(db), str(sauber)]) == 0
    assert main(["--db", str(db), str(belastet)]) == 1

    ausgabe = capsys.readouterr().out

    assert "Musterfirma GmbH" not in ausgabe

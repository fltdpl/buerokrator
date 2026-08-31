import os
import sqlite3
import zipfile
from pathlib import Path

import pytest

from src.core.exceptions import BuerokratorError
from src.services.backup_service import create_backup


def _make_database(path, filename):
    """Echte SQLite-Datei — create_backup liest die DB über die SQLite-API."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, filename TEXT)")
    conn.execute("INSERT INTO documents (filename) VALUES (?)", (filename,))
    conn.commit()
    conn.close()


def test_create_backup_contains_db_and_archive(tmp_path):
    db = tmp_path / "database" / "buerokrator.db"
    db.parent.mkdir()
    _make_database(db, "erste.pdf")

    archive = tmp_path / "archive"
    (archive / "2024" / "Wohnen").mkdir(parents=True)
    (archive / "2024" / "Wohnen" / "miete.pdf").write_bytes(b"PDF")

    target = tmp_path / "backups"

    zip_path = create_backup(
        db_path=db,
        archive_dir=archive,
        target_dir=target,
        backup_name="backup.zip",
    )

    assert zip_path.exists()
    assert zip_path.parent == target

    with zipfile.ZipFile(zip_path) as archive_zip:
        names = set(archive_zip.namelist())

    assert "database/buerokrator.db" in names
    assert "archive/2024/Wohnen/miete.pdf" in names


def test_create_backup_skips_missing_sources(tmp_path):
    # Weder DB noch Archiv vorhanden -> leeres, aber gültiges ZIP.
    zip_path = create_backup(
        db_path=tmp_path / "fehlt.db",
        archive_dir=tmp_path / "kein_archiv",
        target_dir=tmp_path / "backups",
        backup_name="leer.zip",
    )

    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as archive_zip:
        assert archive_zip.namelist() == []


def test_create_backup_creates_target_dir(tmp_path):
    zip_path = create_backup(
        db_path=tmp_path / "fehlt.db",
        archive_dir=tmp_path / "kein_archiv",
        target_dir=tmp_path / "neu" / "tiefer",
        backup_name="b.zip",
    )

    assert zip_path.exists()
    assert (tmp_path / "neu" / "tiefer").is_dir()


# ------------------------------------------------------ Wiederherstellung


def _make_backup(tmp_path):
    from src.services.backup_service import create_backup

    db = tmp_path / "database" / "buerokrator.db"
    db.parent.mkdir()
    _make_database(db, "alt.pdf")

    archive = tmp_path / "archive"
    (archive / "2026" / "Rechnungen").mkdir(parents=True)
    (archive / "2026" / "Rechnungen" / "a.pdf").write_bytes(b"PDF-A")

    return create_backup(db, archive, tmp_path / "backups", "test.zip")


def test_restore_backup_replaces_db_and_archive(tmp_path):
    from src.services.backup_service import restore_backup

    zip_path = _make_backup(tmp_path)

    db = tmp_path / "database" / "buerokrator.db"
    archive = tmp_path / "archive"

    # Stand verändern — die Wiederherstellung muss ihn zurückdrehen.
    db.write_bytes(b"NEUE-DB")
    (archive / "2026" / "Rechnungen" / "b.pdf").write_bytes(b"PDF-B")

    result = restore_backup(zip_path, db_path=db, archive_dir=archive)

    assert result["database"] is True
    assert result["archive_files"] == 1

    restored = sqlite3.connect(db)
    assert [row[0] for row in restored.execute("SELECT filename FROM documents")] == [
        "alt.pdf"
    ]
    restored.close()

    assert (archive / "2026" / "Rechnungen" / "a.pdf").read_bytes() == b"PDF-A"
    assert not (archive / "2026" / "Rechnungen" / "b.pdf").exists()


def test_restore_backup_keeps_previous_state_aside(tmp_path):
    from src.services.backup_service import restore_backup

    zip_path = _make_backup(tmp_path)

    db = tmp_path / "database" / "buerokrator.db"
    archive = tmp_path / "archive"
    db.write_bytes(b"NEUE-DB")

    restore_backup(zip_path, db_path=db, archive_dir=archive)

    # Nichts wird gelöscht: alter Stand liegt beiseite.
    aside_dbs = list((tmp_path / "database").glob("pre_restore_*.db"))
    aside_archives = list(tmp_path.glob("archive_vor_wiederherstellung_*"))

    assert len(aside_dbs) == 1
    assert aside_dbs[0].read_bytes() == b"NEUE-DB"
    assert len(aside_archives) == 1


def test_restore_backup_rejects_zip_without_database(tmp_path):
    import zipfile

    import pytest

    from src.services.backup_service import restore_backup

    bogus = tmp_path / "bogus.zip"
    with zipfile.ZipFile(bogus, "w") as zf:
        zf.writestr("irgendwas.txt", "kein Backup")

    with pytest.raises(ValueError, match="database/"):
        restore_backup(
            bogus,
            db_path=tmp_path / "db.db",
            archive_dir=tmp_path / "archive",
        )


def test_list_backups_newest_first(tmp_path):
    import time

    from src.services.backup_service import list_backups

    target = tmp_path / "backups"
    target.mkdir()
    (target / "alt.zip").write_bytes(b"a")
    time.sleep(0.01)
    (target / "neu.zip").write_bytes(b"b")

    names = [entry["name"] for entry in list_backups(target)]

    assert names == ["neu.zip", "alt.zip"]
    assert list_backups(tmp_path / "fehlt") == []


def test_backup_enthaelt_committete_daten_trotz_offener_wal(tmp_path):
    """Regression: unter WAL lag der Neustand in der -wal-Datei, nicht in der .db.

    Solange irgendeine Verbindung offen ist (laufender Stapel-Import),
    checkpointet SQLite nicht. Ein reines Kopieren der .db-Datei lieferte
    dann eine ZIP ohne die zuletzt importierten Dokumente — still, ohne
    Fehler. Das ist bei einem Backup der schlimmste Fehlermodus.
    """
    db = tmp_path / "database" / "buerokrator.db"
    db.parent.mkdir()

    writer = sqlite3.connect(db)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, filename TEXT)")
    writer.commit()

    # Zweite Verbindung offen halten: verhindert den Checkpoint beim Close.
    reader = sqlite3.connect(db)
    reader.execute("PRAGMA journal_mode=WAL")

    writer.execute("INSERT INTO documents (filename) VALUES ('frisch_importiert.pdf')")
    writer.commit()
    writer.close()

    zip_path = create_backup(
        db_path=db,
        archive_dir=tmp_path / "archive",
        target_dir=tmp_path / "backups",
        backup_name="wal.zip",
    )

    restored = tmp_path / "restored.db"

    with zipfile.ZipFile(zip_path) as backup:
        restored.write_bytes(backup.read("database/buerokrator.db"))

    check = sqlite3.connect(restored)
    filenames = [row[0] for row in check.execute("SELECT filename FROM documents")]
    check.close()
    reader.close()

    assert filenames == ["frisch_importiert.pdf"]


def test_snapshot_bleibt_im_zielordner_und_wird_aufgeraeumt(tmp_path):
    """Die Momentaufnahme ist eine Vollkopie der DB samt OCR-Volltexten.

    Sie darf nicht in /tmp landen (fremdes Dateisystem) und nach dem Backup
    nicht liegen bleiben.
    """
    from src.services.backup_service import _database_snapshot

    db = tmp_path / "database" / "buerokrator.db"
    db.parent.mkdir()
    _make_database(db, "geheim.pdf")

    target = tmp_path / "backups"
    target.mkdir()

    with _database_snapshot(db, target) as snapshot:
        assert target in snapshot.parents
        # mkdtemp legt das Verzeichnis nur für den Besitzer lesbar an.
        assert snapshot.parent.stat().st_mode & 0o077 == 0

    assert not snapshot.exists()

    create_backup(db, tmp_path / "archive", target, "fertig.zip")

    assert [p.name for p in target.iterdir()] == ["fertig.zip"]


# ------------------------------------- Archivpfade nach der Wiederherstellung


def _backup_mit_archivpfaden(tmp_path, pfade):
    """Sicherung, deren DB absolute Pfade eines FREMDEN Ortes trägt."""
    quelle = tmp_path / "quelle"
    db = quelle / "database" / "buerokrator.db"
    db.parent.mkdir(parents=True)

    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE documents (id INTEGER PRIMARY KEY, archive_path TEXT)"
    )
    conn.executemany(
        "INSERT INTO documents (archive_path) VALUES (?)", [(p,) for p in pfade]
    )
    conn.commit()
    conn.close()

    archiv = quelle / "archive"
    (archiv / "2024" / "Wohnen").mkdir(parents=True)
    (archiv / "2024" / "Wohnen" / "miete.pdf").write_bytes(b"PDF")

    return create_backup(db, archiv, tmp_path / "backups", "fremd.zip")


def test_restore_bindet_archivpfade_an_das_neue_archiv(tmp_path):
    """Regression: eine Sicherung, an anderem Ort eingespielt, war unbrauchbar.

    Die Archivdateien landeten am neuen Ort, `archive_path` trug aber weiter
    den Pfad von der Sicherungszeit. Die Folge war still: alle Werte in der
    Detailansicht richtig, nur das PDF "nicht gefunden".
    """
    from src.services.backup_service import restore_backup

    zip_path = _backup_mit_archivpfaden(
        tmp_path, ["/ganz/woanders/archive/2024/Wohnen/miete.pdf"]
    )

    ziel = tmp_path / "ziel"
    db = ziel / "database" / "buerokrator.db"
    archiv = ziel / "archive"

    result = restore_backup(zip_path, db_path=db, archive_dir=archiv)

    assert result["archive_pfade_repariert"] == 1

    conn = sqlite3.connect(db)
    pfade = [row[0] for row in conn.execute("SELECT archive_path FROM documents")]
    conn.close()

    # Speicherform seit Schema v7: relativ zur Basis (dem Elternverzeichnis
    # des Archivs) — so übersteht der wiederhergestellte Bestand auch den
    # nächsten Ortswechsel, ohne erneut gebunden werden zu müssen.
    assert pfade == [str(Path("archive") / "2024" / "Wohnen" / "miete.pdf")]


def test_restore_legt_keine_zweite_sicherung_an(tmp_path):
    """Der alte Stand liegt schon als pre_restore beiseite — das genügt."""
    from src.services.backup_service import restore_backup

    zip_path = _backup_mit_archivpfaden(
        tmp_path, ["/ganz/woanders/archive/2024/Wohnen/miete.pdf"]
    )

    ziel = tmp_path / "ziel"
    db = ziel / "database" / "buerokrator.db"

    restore_backup(zip_path, db_path=db, archive_dir=ziel / "archive")

    assert list(db.parent.glob("pre_pfadreparatur_*.db")) == []


def test_restore_gelingt_auch_wenn_die_pfadbindung_scheitert(tmp_path, caplog):
    """Die Nachbesserung darf eine Wiederherstellung nie zu Fall bringen.

    Die Dateien liegen zu diesem Zeitpunkt schon am Ziel; ein Abbruch ließe
    den Nutzer mit halb ausgepacktem Bestand zurück. Hier fehlt der
    gesicherten Datenbank die Spalte archive_path.
    """
    import logging

    from src.services.backup_service import restore_backup

    zip_path = _make_backup(tmp_path)

    ziel = tmp_path / "ziel"

    with caplog.at_level(logging.WARNING):
        result = restore_backup(
            zip_path,
            db_path=ziel / "database" / "buerokrator.db",
            archive_dir=ziel / "archive",
        )

    assert result["database"] is True
    assert result["archive_pfade_repariert"] == 0
    assert "Archivpfade" in caplog.text


# ------------------------------------------------ Konfiguration des Profils


def _config_ordner(tmp_path, inhalt="Musterfirma GmbH: Musterfirma\n"):
    ordner = tmp_path / "config"
    ordner.mkdir()
    (ordner / "aussteller_aliase.yaml").write_text(inhalt, encoding="utf-8")

    return ordner


def test_backup_enthaelt_die_profil_konfiguration(tmp_path):
    """Die Aussteller-Aliase sind Handarbeit von Monaten und stehen in keiner
    Datenbank — ohne sie ist der wiederhergestellte Bestand unvollständig."""
    from src.services.backup_service import create_backup

    zip_path = create_backup(
        db_path=tmp_path / "fehlt.db",
        archive_dir=tmp_path / "kein_archiv",
        config_dir=_config_ordner(tmp_path),
        target_dir=tmp_path / "backups",
        backup_name="b.zip",
    )

    with zipfile.ZipFile(zip_path) as archive:
        assert "config/aussteller_aliase.yaml" in archive.namelist()


def test_backup_ohne_konfiguration_bleibt_gueltig(tmp_path):
    """Ein frisches System hat noch keine Aliasdatei."""
    from src.services.backup_service import create_backup

    zip_path = create_backup(
        db_path=tmp_path / "fehlt.db",
        archive_dir=tmp_path / "kein_archiv",
        config_dir=tmp_path / "kein_config",
        target_dir=tmp_path / "backups",
        backup_name="b.zip",
    )

    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == []


def test_restore_spielt_die_konfiguration_zurueck(tmp_path):
    from src.services.backup_service import create_backup, restore_backup

    quelle = tmp_path / "quelle"
    quelle.mkdir()
    db = quelle / "buerokrator.db"
    _make_database(db, "erste.pdf")

    zip_path = create_backup(
        db_path=db,
        archive_dir=quelle / "archive",
        config_dir=_config_ordner(quelle, "Alt AG: Alt\n"),
        target_dir=tmp_path / "backups",
        backup_name="b.zip",
    )

    ziel = tmp_path / "ziel"
    ziel.mkdir()

    restore_backup(
        zip_path,
        db_path=ziel / "buerokrator.db",
        archive_dir=ziel / "archive",
        config_dir=ziel / "config",
    )

    assert (ziel / "config" / "aussteller_aliase.yaml").read_text(
        encoding="utf-8"
    ) == "Alt AG: Alt\n"


def test_restore_legt_die_bisherige_konfiguration_beiseite(tmp_path):
    """Nichts wird gelöscht — auch hier nicht."""
    from src.services.backup_service import create_backup, restore_backup

    quelle = tmp_path / "quelle"
    quelle.mkdir()
    db = quelle / "buerokrator.db"
    _make_database(db, "erste.pdf")

    zip_path = create_backup(
        db_path=db,
        archive_dir=quelle / "archive",
        config_dir=_config_ordner(quelle, "Aus der Sicherung: X\n"),
        target_dir=tmp_path / "backups",
        backup_name="b.zip",
    )

    ziel = tmp_path / "ziel"
    ziel.mkdir()
    _config_ordner(ziel, "Von heute: Y\n")

    restore_backup(
        zip_path,
        db_path=ziel / "buerokrator.db",
        archive_dir=ziel / "archive",
        config_dir=ziel / "config",
    )

    beiseite = list(ziel.glob("config_vor_wiederherstellung_*"))

    assert len(beiseite) == 1
    assert (beiseite[0] / "aussteller_aliase.yaml").read_text(
        encoding="utf-8"
    ) == "Von heute: Y\n"


def test_alte_sicherung_ohne_config_laesst_die_aliase_stehen(tmp_path):
    """Sicherungen aus früheren Fassungen bleiben gültig — und dürfen die
    gepflegte Aliasdatei nicht wegräumen, nur weil sie keine mitbringen."""
    from src.services.backup_service import create_backup, restore_backup

    quelle = tmp_path / "quelle"
    quelle.mkdir()
    db = quelle / "buerokrator.db"
    _make_database(db, "erste.pdf")

    zip_path = create_backup(
        db_path=db,
        archive_dir=quelle / "archive",
        target_dir=tmp_path / "backups",
        backup_name="alt.zip",
    )

    ziel = tmp_path / "ziel"
    ziel.mkdir()
    _config_ordner(ziel, "Gepflegt: Z\n")

    restore_backup(
        zip_path,
        db_path=ziel / "buerokrator.db",
        archive_dir=ziel / "archive",
        config_dir=ziel / "config",
    )

    assert (ziel / "config" / "aussteller_aliase.yaml").read_text(
        encoding="utf-8"
    ) == "Gepflegt: Z\n"
    assert not list(ziel.glob("config_vor_wiederherstellung_*"))


# ------------------------------------------------- Pruefung nach dem Packen


def test_sicherung_wird_nach_dem_schreiben_geprueft(tmp_path):
    """Eine volle Platte oder ein abbrechender Stick hinterlassen eine Datei,
    die aussieht wie eine Sicherung. Ungeprüft fiele das erst beim
    Wiederherstellen auf — Jahre später."""
    from src.services.backup_service import pruefe_sicherung

    zip_path = tmp_path / "b.zip"
    name = "database/buerokrator.db"

    # Zufallsbytes: sie komprimieren nicht, der Datenbereich ist dadurch so
    # groß wie die Nutzlast und mit einem Offset sicher zu treffen. Mit gut
    # komprimierbarem Inhalt schrumpft er auf wenige Bytes — ein Treffer
    # daneben landet im Verzeichnisteil und bleibt folgenlos (so ist dieser
    # Test beim ersten Anlauf durchgelaufen, ohne etwas zu prüfen).
    nutzlast = os.urandom(5000)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, nutzlast)

    # Heil: keine Beanstandung.
    pruefe_sicherung(zip_path, [name])

    with zipfile.ZipFile(zip_path) as archive:
        info = archive.getinfo(name)
        datenanfang = info.header_offset + 30 + len(name)

    roh = bytearray(zip_path.read_bytes())
    roh[datenanfang + 2000] ^= 0xFF
    zip_path.write_bytes(bytes(roh))

    with pytest.raises(BuerokratorError):
        pruefe_sicherung(zip_path, [name])


def test_pruefung_meldet_fehlende_eintraege(tmp_path):
    from src.services.backup_service import pruefe_sicherung

    zip_path = tmp_path / "b.zip"

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("database/buerokrator.db", "x")

    with pytest.raises(BuerokratorError) as fehler:
        pruefe_sicherung(zip_path, ["database/buerokrator.db", "archive/a.pdf"])

    assert "archive/a.pdf" in str(fehler.value)


def test_create_backup_prueft_das_ergebnis(tmp_path):
    """Die Prüfung gehört in create_backup, nicht nur in die Oberfläche —
    sonst hat der eine Aufrufer sie und der andere nicht."""
    import src.services.backup_service as backup_service

    db = tmp_path / "buerokrator.db"
    _make_database(db, "erste.pdf")

    geprueft = []
    backup_service.pruefe_sicherung  # existiert?

    original = backup_service.pruefe_sicherung
    backup_service.pruefe_sicherung = lambda pfad, erwartet: geprueft.append(
        sorted(erwartet)
    )

    try:
        backup_service.create_backup(
            db_path=db,
            archive_dir=tmp_path / "kein_archiv",
            target_dir=tmp_path / "backups",
            backup_name="b.zip",
        )

    finally:
        backup_service.pruefe_sicherung = original

    assert geprueft == [["database/buerokrator.db"]]


def test_beschaedigte_sicherung_gilt_nicht_als_sicherung(tmp_path):
    """Bliebe die kaputte Datei als .zip liegen, gälte sie als die jüngste
    Sicherung — das Dashboard meldete Entwarnung für einen Datenmüllhaufen.
    Gelöscht wird sie trotzdem nicht."""
    import src.services.backup_service as backup_service
    from src.services.backup_service import list_backups

    db = tmp_path / "buerokrator.db"
    _make_database(db, "erste.pdf")

    original = backup_service.pruefe_sicherung

    def scheitert(pfad, erwartet):
        raise BuerokratorError("Prüfsumme falsch")

    backup_service.pruefe_sicherung = scheitert

    try:
        with pytest.raises(BuerokratorError):
            backup_service.create_backup(
                db_path=db,
                archive_dir=tmp_path / "kein_archiv",
                target_dir=tmp_path / "backups",
                backup_name="b.zip",
            )

    finally:
        backup_service.pruefe_sicherung = original

    ziel = tmp_path / "backups"

    assert list_backups(ziel) == []
    assert (ziel / "b.zip.unvollstaendig").exists()

import sqlite3
import zipfile

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

    assert pfade == [str(archiv / "2024" / "Wohnen" / "miete.pdf")]


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

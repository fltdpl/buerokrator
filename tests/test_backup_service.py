import zipfile

from src.services.backup_service import create_backup


def test_create_backup_contains_db_and_archive(tmp_path):
    db = tmp_path / "database" / "buerokrator.db"
    db.parent.mkdir()
    db.write_bytes(b"SQLITE")

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
    db.write_bytes(b"ALTE-DB")

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

    assert result == {"database": True, "archive_files": 1}
    assert db.read_bytes() == b"ALTE-DB"
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

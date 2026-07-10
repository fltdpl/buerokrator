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

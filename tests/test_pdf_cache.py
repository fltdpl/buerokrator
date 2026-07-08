from src.gui.pdf_cache import cleanup_pdf_cache, remove_cached_pdf


def test_cleanup_removes_orphans_and_keeps_valid(tmp_path):
    (tmp_path / "1.pdf").write_bytes(b"a")
    (tmp_path / "2.pdf").write_bytes(b"b")
    (tmp_path / "99.pdf").write_bytes(b"orphan")
    # Nicht dem Schema entsprechende Dateien werden ebenfalls entfernt.
    (tmp_path / "kaputt.pdf").write_bytes(b"x")
    (tmp_path / "1.txt").write_bytes(b"x")

    removed = cleanup_pdf_cache([1, 2], base_dir=tmp_path)

    assert removed == 3
    assert sorted(p.name for p in tmp_path.iterdir()) == ["1.pdf", "2.pdf"]


def test_cleanup_with_missing_dir_is_noop(tmp_path):
    assert cleanup_pdf_cache([1], base_dir=tmp_path / "gibtsnicht") == 0


def test_remove_cached_pdf(tmp_path):
    (tmp_path / "7.pdf").write_bytes(b"x")

    remove_cached_pdf(7, base_dir=tmp_path)
    # Zweiter Aufruf (Datei fehlt) darf nicht fehlschlagen.
    remove_cached_pdf(7, base_dir=tmp_path)

    assert not (tmp_path / "7.pdf").exists()

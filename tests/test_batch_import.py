import src.processor.batch_import as batch_import


def write_config(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                "  inbox: ./inbox",
                "  archive: ./archive",
                "  exports: ./exports",
                "database:",
                "  path: ./database/buerokrator.db",
                "supported_file_types:",
                "  - .pdf",
                "  - .png",
            ]
        ),
        encoding="utf-8",
    )


def test_find_inbox_documents_filters_supported_types(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "a.pdf").write_text("x")
    (inbox / "b.png").write_text("x")
    (inbox / "c.txt").write_text("x")
    (inbox / "sub").mkdir()

    found = [p.name for p in batch_import.find_inbox_documents()]

    assert found == ["a.pdf", "b.png"]


def test_find_inbox_documents_without_inbox_returns_empty(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert batch_import.find_inbox_documents() == []


def test_import_inbox_documents_splits_success_and_failure(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "ok.pdf").write_text("x")
    (inbox / "bad.pdf").write_text("x")

    # process durch ein Fake ersetzen: bad.pdf schlägt fehl.
    def fake_process(file_path):
        return not file_path.endswith("bad.pdf")

    monkeypatch.setattr(batch_import, "process", fake_process)

    calls = []
    succeeded, failed = batch_import.import_inbox_documents(
        lambda index, total, name: calls.append((index, total, name))
    )

    assert succeeded == ["ok.pdf"]
    assert failed == ["bad.pdf"]
    # progress_callback für jede Datei aufgerufen.
    assert len(calls) == 2
    assert calls[0][1] == 2

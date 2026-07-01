from src.database.database import get_connection
from src.database.document_repository import insert_document
from src.database.init_database import init_database
from src.database.list_documents import list_documents
from src.database.reset_database import reset_database_and_archive


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
            ]
        ),
        encoding="utf-8",
    )


def test_reset_clears_archive_and_documents(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    init_database()
    insert_document("a.pdf", "archive/2024/Rechnungen/a.pdf", "invoice", {"amount": 10})
    insert_document("b.pdf", "archive/2024/Bank/b.pdf", "bank", {})

    assert len(list_documents()) == 2

    # Archivinhalte anlegen: ein Jahresordner und eine lose Datei.
    nested = tmp_path / "archive" / "2024" / "Rechnungen"
    nested.mkdir(parents=True)
    (nested / "a.pdf").write_text("x")
    (tmp_path / "archive" / "lose.txt").write_text("y")

    removed = reset_database_and_archive()

    # Archivordner bleibt, Inhalte sind weg.
    assert (tmp_path / "archive").exists()
    assert list((tmp_path / "archive").iterdir()) == []
    assert removed == 2

    # Datenbank ist leer.
    assert list_documents() == []

    # Schema wurde neu initialisiert (Tabelle mit id-Spalte vorhanden).
    conn = get_connection()
    columns = conn.execute("PRAGMA table_info(documents)").fetchall()
    conn.close()

    assert any(column[1] == "id" for column in columns)


def test_reset_on_empty_archive_does_not_fail(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    init_database()

    # Kein Archivordner vorhanden -> darf nicht crashen, 0 entfernt.
    removed = reset_database_and_archive()

    assert removed == 0
    assert list_documents() == []

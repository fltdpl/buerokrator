"""Smoke-Tests für das NiceGUI-Frontend (User-Fixture, ohne Browser).

Läuft gegen eine leere Test-Datenbank (tmp_path): prüft, dass alle Seiten
fehlerfrei bauen und die Kern-Navigation funktioniert.
"""

import pytest

from nicegui.testing import User

pytest_plugins = ["nicegui.testing.user_plugin"]


@pytest.fixture(autouse=True)
def isolated_project(tmp_path, monkeypatch):
    """Leere Config + DB, damit die Tests nie die echte Datenbank berühren."""
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
                "classifier:",
                "  model: gemma3:4b",
                "  temperature: 0.0",
                "  max_input_chars: 3000",
                "ocr:",
                "  language: deu+eng",
                "  tesseract:",
                "    windows: C:/Program Files/Tesseract-OCR/tesseract.exe",
                "    linux: /usr/bin/tesseract",
                "  poppler:",
                "    windows: \"\"",
                "    linux: \"\"",
                "logging:",
                "  level: INFO",
                "supported_file_types:",
                "  - .pdf",
                "archive:",
                "  category_mapping:",
                "    invoice: Rechnungen",
                "    tax: Steuern",
                "    insurance: Versicherungen",
                "    pension: Vorsorge",
                "    bank: Bank",
                "    housing: Wohnen",
                "    employment: Arbeit",
                "    legal: Recht",
                "    unknown: Sonstiges",
            ]
        ),
        encoding="utf-8",
    )
    # NiceGUI beobachtet sein Storage-Verzeichnis; ohne das Verzeichnis
    # schlägt der Watchdog beim App-Start fehl.
    (tmp_path / ".nicegui").mkdir()
    monkeypatch.chdir(tmp_path)

    from src.database.init_database import init_database

    init_database()


@pytest.mark.asyncio
async def test_dashboard_renders(user: User):
    await user.open("/")
    await user.should_see("Dashboard")
    await user.should_see("Dokumente archiviert")


@pytest.mark.asyncio
async def test_documents_list_renders_empty(user: User):
    await user.open("/dokumente")
    await user.should_see("Keine Dokumente gefunden.")


@pytest.mark.asyncio
async def test_document_detail_renders(user: User):
    from src.database.document_repository import insert_document

    document_id = insert_document(
        "2024-01-01_Amazon_42EUR.pdf",
        "archive/2024/Rechnungen/2024-01-01_Amazon_42EUR.pdf",
        "invoice",
        {"issuer": "Amazon", "amount": 42.0, "document_date": "01.01.2024"},
    )

    await user.open(f"/dokumente/{document_id}")
    await user.should_see("Speichern & Freigeben")
    await user.should_see("Aussteller")
    # Dokument-ID im Kopf sichtbar.
    await user.should_see(f"ID {document_id}")


@pytest.mark.asyncio
async def test_employment_detail_shows_subject_and_tax_relevant(user: User):
    from src.database.document_repository import insert_document

    document_id = insert_document(
        "2024-03-01_ACME_Kuendigung.pdf",
        "archive/2024/Arbeit/2024-03-01_ACME_Kuendigung.pdf",
        "employment",
        {
            "document_subtype": "kuendigung",
            "issuer": "ACME AG",
            "document_date": "01.03.2024",
            "subject": "Ordentliche Kündigung",
        },
    )

    await user.open(f"/dokumente/{document_id}")
    await user.should_see("Arbeit")
    await user.should_see("Betreff")
    await user.should_see("Steuerrelevant")


@pytest.mark.asyncio
async def test_document_detail_unknown_id(user: User):
    await user.open("/dokumente/99999")
    await user.should_see("Dokument nicht gefunden.")


@pytest.mark.asyncio
async def test_import_page_renders(user: User):
    await user.open("/import")
    await user.should_see("Stapel-Import")
    await user.should_see("Keine Dateien im Inbox-Ordner.")


@pytest.mark.asyncio
async def test_tax_page_renders_empty(user: User):
    await user.open("/steuer")
    await user.should_see("Noch keine archivierten Dokumente vorhanden.")


@pytest.mark.asyncio
async def test_settings_page_renders(user: User):
    await user.open("/einstellungen")
    await user.should_see("Einstellungen")
    await user.should_see("Gefahrenzone")


@pytest.mark.asyncio
async def test_trash_page_renders_empty(user: User):
    await user.open("/papierkorb")
    await user.should_see("Der Papierkorb ist leer.")


@pytest.mark.asyncio
async def test_trash_page_lists_deleted_files(user: User, tmp_path):
    trash = tmp_path / "trash"
    trash.mkdir()
    (trash / "geloescht.pdf").write_text("x", encoding="utf-8")

    await user.open("/papierkorb")
    await user.should_see("geloescht.pdf")
    await user.should_see("Wiederherstellen")


@pytest.mark.asyncio
async def test_detail_marks_empty_required_field(user: User):
    from src.database.document_repository import insert_document

    # Ohne Aussteller: das Feld ist Pflicht und muss beim Prüfen auffallen.
    document_id = insert_document(
        "2024-01-01_unbekannt.pdf",
        "archive/2024/Rechnungen/2024-01-01_unbekannt.pdf",
        "invoice",
        {"amount": 42.0, "document_date": "01.01.2024"},
    )

    await user.open(f"/dokumente/{document_id}")
    await user.should_see("Pflichtfeld(er) leer")

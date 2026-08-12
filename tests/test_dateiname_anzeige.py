"""Dateinamen: gekürzt auf dem Dashboard, sichtbar in der Detailansicht.

Der Dateiname trägt Datum, Aussteller und Betreff — er wird dadurch lang.
Auf dem Dashboard lief er über den Rand der Karte „Zuletzt archiviert“
hinaus; in der Detailansicht war er dagegen nirgends zu sehen, obwohl genau
dort die Frage aufkommt, wie die Datei im Archiv heißt.
"""

import pytest
from nicegui.testing import User

pytest_plugins = ["nicegui.testing.user_plugin"]

# Lang genug, um in jeder vernünftigen Spaltenbreite zu überlaufen.
LANGER_NAME = (
    "2026-03-15_Musterkasse-Sued-West_Beitragsbescheinigung-fuer-die-"
    "Steuererklaerung-2025_Nachtrag-zur-Vorversicherung_Seite-1-von-3.pdf"
)


@pytest.fixture(autouse=True)
def isolated_project(tmp_path, monkeypatch):
    """Leere Config + DB — dieselbe Isolation wie im Frontend-Smoke."""
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
                "logging:",
                "  level: INFO",
                "supported_file_types:",
                "  - .pdf",
                "archive:",
                "  category_mapping:",
                "    invoice: Rechnungen",
                "    unknown: Sonstiges",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".nicegui").mkdir()
    monkeypatch.chdir(tmp_path)

    from src.database.init_database import init_database

    init_database()


def _dokument(name=LANGER_NAME):
    from src.database.document_repository import insert_document

    return insert_document(
        name,
        f"archive/2026/Rechnungen/{name}",
        "invoice",
        {"issuer": "Musterkasse", "amount": 42.0, "document_date": "15.03.2026"},
    )


@pytest.mark.asyncio
async def test_dashboard_kuerzt_lange_dateinamen(user: User):
    """Der Name darf die Karte nicht sprengen — gekürzt wird per CSS.

    Bewusst über die Klasse geprüft und nicht über den Text: die Kürzung
    macht der Browser anhand der verfügbaren Breite, im Markup steht
    weiterhin der volle Name. Genau das ist gewollt (Suchen, Kopieren).
    """
    _dokument()

    await user.open("/")
    await user.should_see(LANGER_NAME)

    treffer = list(user.find(LANGER_NAME).elements)
    link = next(element for element in treffer if "truncate" in element.classes)

    # Ohne min-w-0 ignoriert ein Flex-Kind die Kürzung und drückt statt zu
    # kürzen — die Klasse allein reicht nicht.
    assert "min-w-0" in link.classes


@pytest.mark.asyncio
async def test_dashboard_zeigt_den_vollen_namen_im_tooltip(user: User):
    _dokument()

    await user.open("/")

    treffer = list(user.find(LANGER_NAME).elements)
    link = next(element for element in treffer if "truncate" in element.classes)

    assert link._props.get("title") == LANGER_NAME


@pytest.mark.asyncio
async def test_detailansicht_zeigt_den_dateinamen(user: User):
    document_id = _dokument()

    await user.open(f"/dokumente/{document_id}")
    await user.should_see(LANGER_NAME)


@pytest.mark.asyncio
async def test_dateiname_in_der_detailansicht_ist_gekuerzt(user: User):
    document_id = _dokument()

    await user.open(f"/dokumente/{document_id}")

    treffer = list(user.find(LANGER_NAME).elements)
    label = next(element for element in treffer if "truncate" in element.classes)

    assert "min-w-0" in label.classes
    assert label._props.get("title") == LANGER_NAME


@pytest.mark.asyncio
async def test_dashboard_vertraegt_dokument_ohne_dateinamen(user: User):
    """Regression: `gekuerzt` liess das ganze Dashboard abstuerzen.

    `filename` ist nullable — es gibt Zeilen ohne Namen (gefunden vom
    Umzugs-Test, nicht konstruiert). Ein fehlender Name darf hoechstens die
    eine Zeile leer lassen, nie die Seite.
    """
    from src.database.document_repository import insert_document

    insert_document(None, "archive/2026/Sonstiges/ohne.pdf", "unknown", {})

    await user.open("/")
    await user.should_see("Zuletzt archiviert")

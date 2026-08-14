"""Rückmeldung nach „💾 Speichern" und Anzeige ohne Dateinamen.

Seit dem Fix vom 06.08.2026 gibt „Speichern" das Dokument nicht mehr still
frei — damit fiel aber auch die einzige sichtbare Bestätigung weg: der
Status blieb 🟡, die Seite lud neu und sah gleich aus. `ui.notify` überlebt
`ui.navigate.to()` nicht, die Meldung muss also über die neue Seite kommen.
"""

import pytest
from nicegui.testing import User

pytest_plugins = ["nicegui.testing.user_plugin"]


@pytest.fixture(autouse=True)
def isolated_project(tmp_path, monkeypatch):
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


def _dokument(name="2026-04-01_Musterversand_Rechnung.pdf"):
    from src.database.document_repository import insert_document

    return insert_document(
        name,
        f"archive/2026/Rechnungen/{name}",
        "invoice",
        {"issuer": "Musterversand", "amount": 42.0, "document_date": "01.04.2026"},
    )


@pytest.mark.asyncio
async def test_gespeichert_parameter_zeigt_bestaetigung(user: User):
    """Die Meldung kommt über die neu geladene Seite, nicht über notify davor."""
    document_id = _dokument()

    await user.open(f"/dokumente/{document_id}?gespeichert=1")
    await user.should_see("Gespeichert")


@pytest.mark.asyncio
async def test_ohne_parameter_keine_bestaetigung(user: User):
    """Ein normaler Aufruf darf nichts melden — sonst wird die Meldung Tapete."""
    document_id = _dokument()

    await user.open(f"/dokumente/{document_id}")
    await user.should_not_see("Gespeichert")


@pytest.mark.asyncio
async def test_speichern_haengt_den_parameter_an(user: User):
    """Der Knopf muss auf die Adresse MIT Parameter navigieren.

    Ohne diesen Test wäre die Meldung zwar baubar, aber unerreichbar — die
    Kette Knopf → Adresse → Meldung ist der eigentliche Gegenstand.
    """
    from nicegui import ui

    document_id = _dokument()
    ziele = []

    await user.open(f"/dokumente/{document_id}")

    user.client.__class__  # sicherstellen, dass die Seite steht
    original = ui.navigate.to
    ui.navigate.to = lambda ziel, *args, **kwargs: ziele.append(str(ziel))

    try:
        user.find("💾 Speichern").click()

    finally:
        ui.navigate.to = original

    assert ziele == [f"/dokumente/{document_id}?gespeichert=1"]


@pytest.mark.asyncio
async def test_freigeben_meldet_nicht_zusaetzlich(user: User):
    """Freigeben blättert weiter — dort wäre die Meldung fehl am Platz.

    Der Statuswechsel 🟡 → 🟢 ist die Rückmeldung; eine zweite auf dem
    NÄCHSTEN Dokument würde sich auf dessen Inhalt zu beziehen scheinen.
    """
    from nicegui import ui

    document_id = _dokument()
    ziele = []

    await user.open(f"/dokumente/{document_id}")

    original = ui.navigate.to
    ui.navigate.to = lambda ziel, *args, **kwargs: ziele.append(str(ziel))

    try:
        user.find("✅ Speichern & Freigeben").click()

    finally:
        ui.navigate.to = original

    assert ziele
    assert all("gespeichert" not in ziel for ziel in ziele)


@pytest.mark.asyncio
async def test_dashboard_zeigt_ersatztext_ohne_dateinamen(user: User):
    """Ein Link ohne Text ist unklickbar — die Zeile braucht einen Anker."""
    from src.database.document_repository import insert_document

    document_id = insert_document(
        None, "archive/2026/Sonstiges/ohne.pdf", "unknown", {}
    )

    await user.open("/")
    await user.should_see(f"#{document_id} (ohne Dateinamen)")

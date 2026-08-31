"""Die OCR-Textansicht muss so hoch sein wie die PDF-Ansicht daneben.

Die Hoehe stand am aeusseren Feld-Wrapper — dort verpufft sie: Quasar setzt
`.q-textarea .q-field__control` auf `height: auto`, sodass der Rahmen sich
nach dem inneren `<textarea>` richtet und auf dessen Standard von wenigen
Zeilen zusammenfaellt. Sichtbar war ein schmales Fenster, egal wie lang der
erkannte Text war. Die Hoehe gehoert deshalb ueber `input-style` an das
native Feld.
"""

import pytest
from nicegui import ui
from nicegui.testing import User

pytest_plugins = ["nicegui.testing.user_plugin"]


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


# Laenger als jedes Textfeld hoch sein kann — der Text ist erfunden.
LANGER_OCR_TEXT = "\n".join(f"Zeile {nummer} des erkannten Textes" for nummer in range(80))


def _dokument(text=LANGER_OCR_TEXT):
    from src.database.document_repository import insert_document

    return insert_document(
        "2026-03-15_Musterfirma-GmbH_Rechnung.pdf",
        "archive/2026/Rechnungen/2026-03-15_Musterfirma-GmbH_Rechnung.pdf",
        "invoice",
        {
            "issuer": "Musterfirma GmbH",
            "amount": 42.0,
            "document_date": "15.03.2026",
        },
        document_text=text,
    )


def _quelltext_feld(user: User):
    """Das OCR-Textfeld — erkennbar an `readonly`, anders als die Notizen."""
    return next(
        element
        for element in user.client.elements.values()
        if isinstance(element, ui.textarea) and element._props.get("readonly")
    )


def _pdf_rahmen(user: User):
    return next(
        element
        for element in user.client.elements.values()
        if getattr(element, "tag", None) == "iframe"
    )


@pytest.mark.asyncio
async def test_ocr_textfeld_bekommt_die_hoehe_am_nativen_feld(user: User):
    """Regression: `.style("height: …")` allein blieb wirkungslos.

    Geprueft wird `input-style`, nicht die Wrapper-Hoehe: nur was Quasar an
    das innere `<textarea>` durchreicht, ueberlebt dessen `height: auto`.
    """
    from src.frontend.pages.document_detail import QUELLE_HOEHE

    document_id = _dokument()

    await user.open(f"/dokumente/{document_id}")

    feld = _quelltext_feld(user)

    assert QUELLE_HOEHE in feld._props.get("input-style", "")


@pytest.mark.asyncio
async def test_pdf_und_text_sind_gleich_hoch(user: User):
    """Beide Ansichten teilen dieselbe Hoehe — sonst springt das Layout.

    Der Umschalter tauscht die Ansichten an Ort und Stelle; unterschiedliche
    Hoehen liessen die Karte bei jedem Klick wachsen und schrumpfen.
    """
    from src.frontend.pages.document_detail import QUELLE_HOEHE

    document_id = _dokument()

    await user.open(f"/dokumente/{document_id}")

    rahmen = _pdf_rahmen(user)

    assert QUELLE_HOEHE in rahmen._style.get("height", "")
    assert QUELLE_HOEHE in _quelltext_feld(user)._props.get("input-style", "")

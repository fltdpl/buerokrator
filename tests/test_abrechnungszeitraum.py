"""Abrechnungszeitraum bei Wohnen-Abrechnungen.

Nebenkostenabrechnungen kommen oft Jahre nach dem Zeitraum, den sie
abrechnen. Archivordner und Steuerjahr richten sich nach dem ZUGANG
(Dokumentdatum, siehe docs/04_Steuerlogik.md) — der Zeitraum soll das nicht
verschieben, sondern nur festhalten, welches Jahr die Abrechnung betrifft.
Alle Namen und Beträge sind erfunden.
"""

from pathlib import Path

import pytest
from nicegui.testing import User

from src.classifier.document_extractor import PROMPT_FILES
from src.core.document_fields import whitelist_fields
from src.core.document_types import HOUSING
from src.organizer.date_utils import extract_year
from src.organizer.filename_builder import build_filename
from src.services.form_schema import form_fields

pytest_plugins = ["nicegui.testing.user_plugin"]

PROMPTS = Path(__file__).resolve().parents[1] / "src" / "classifier" / "prompts"

ABRECHNUNGEN = ("nebenkostenabrechnung", "heizkostenabrechnung", "hausgeldabrechnung")


def _abrechnung(**felder):
    return {
        "document_subtype": "nebenkostenabrechnung",
        "issuer": "Musterhausverwaltung",
        "document_date": "14.03.2024",
        "period_start": "01.01.2021",
        "period_end": "31.12.2021",
        "settlement_amount": 187.4,
        **felder,
    }


@pytest.mark.parametrize("unterart", ABRECHNUNGEN)
def test_whitelist_haelt_den_zeitraum_bei_abrechnungen(unterart):
    result = whitelist_fields(HOUSING, _abrechnung(document_subtype=unterart))

    assert result["period_start"] == "01.01.2021"
    assert result["period_end"] == "31.12.2021"


def test_whitelist_verwirft_den_zeitraum_beim_mietvertrag():
    result = whitelist_fields(HOUSING, _abrechnung(document_subtype="mietvertrag"))

    assert "period_start" not in result
    assert "period_end" not in result


@pytest.mark.parametrize("unterart", ABRECHNUNGEN)
def test_formular_fuehrt_den_zeitraum_bei_abrechnungen(unterart):
    labels = {field["key"]: field["label"] for field in form_fields(HOUSING, unterart)}

    assert labels["period_start"] == "Abrechnungszeitraum von"
    assert labels["period_end"] == "Abrechnungszeitraum bis"


def test_formular_fuehrt_keinen_zeitraum_beim_mietvertrag():
    keys = {field["key"] for field in form_fields(HOUSING, "mietvertrag")}

    assert "period_start" not in keys


def test_prompt_fragt_den_zeitraum_ab():
    prompt = (PROMPTS / PROMPT_FILES[HOUSING]).read_text(encoding="utf-8")

    assert '"period_start"' in prompt
    assert '"period_end"' in prompt


def test_archivjahr_bleibt_das_jahr_des_zugangs():
    # Der Kern der Sache: eine 2024 zugegangene Abrechnung für 2021 gehört in
    # den Ordner und die Steuererklärung 2024.
    assert extract_year(_abrechnung()) == "2024"


def _dateiname(**felder):
    return build_filename({"document_type": HOUSING}, _abrechnung(**felder), "scan.pdf")


def test_dateiname_traegt_das_abgerechnete_jahr():
    name = _dateiname()

    assert name.startswith("2024-03-14_")
    assert name.endswith("_2021.pdf")


def test_dateiname_bei_zeitraum_ueber_den_jahreswechsel():
    assert _dateiname(period_start="01.07.2021", period_end="30.06.2022").endswith(
        "_2021-22.pdf"
    )


def test_dateiname_mit_nur_einem_ende_des_zeitraums():
    assert _dateiname(period_end=None).endswith("_2021.pdf")
    assert _dateiname(period_start=None).endswith("_2021.pdf")


def test_dateiname_ohne_zeitraum_bleibt_wie_bisher():
    name = _dateiname(period_start=None, period_end=None)

    assert name == "2024-03-14_Musterhausverwaltung_nebenkostenabrechnung.pdf"


# --- Oberfläche -----------------------------------------------------------


@pytest.fixture
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
                "    housing: Wohnen",
                "    unknown: Sonstiges",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".nicegui").mkdir()
    monkeypatch.chdir(tmp_path)

    from src.database.init_database import init_database

    init_database()


def _dokument(unterart="nebenkostenabrechnung"):
    from src.database.document_repository import insert_document

    name = "2024-03-14_Musterhausverwaltung_nebenkostenabrechnung_2021.pdf"

    return insert_document(
        name,
        f"archive/2024/Wohnen/{name}",
        HOUSING,
        _abrechnung(document_subtype=unterart),
    )


@pytest.mark.asyncio
async def test_abrechnung_zeigt_das_steuerjahr_des_zugangs(user: User, isolated_project):
    document_id = _dokument()

    await user.open(f"/dokumente/{document_id}")

    await user.should_see("Steuerjahr: 2024 (Jahr des Zugangs)")


@pytest.mark.asyncio
async def test_erklaerung_oeffnet_sich_erst_auf_klick(user: User, isolated_project):
    document_id = _dokument()

    await user.open(f"/dokumente/{document_id}")

    # Der Simulator meldet auch den Inhalt eines GESCHLOSSENEN Dialogs als
    # sichtbar — should_not_see wäre hier immer rot. Deshalb am Zustand des
    # Dialogs selbst prüfen.
    dialog = _erklaerungsdialog(user)
    assert dialog.value is False

    user.find(marker="steuerjahr-info").click()

    assert dialog.value is True


def _erklaerungsdialog(user: User):
    from nicegui import ui

    from src.frontend.pages.document_detail import STEUERJAHR_ERKLAERUNG

    return next(
        element
        for element in user.client.elements.values()
        if isinstance(element, ui.dialog)
        and any(
            getattr(kind, "text", None) == STEUERJAHR_ERKLAERUNG
            for kind in element.descendants()
        )
    )


@pytest.mark.asyncio
async def test_mietvertrag_zeigt_keine_steuerjahr_zeile(user: User, isolated_project):
    document_id = _dokument(unterart="mietvertrag")

    await user.open(f"/dokumente/{document_id}")

    await user.should_not_see("Jahr des Zugangs")

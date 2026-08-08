"""Oberfläche der Profile (ADR 015, Schritt 4).

Zwei Zusagen stehen im Mittelpunkt: ohne zweite Person sieht die App aus wie
vorher — und sobald es sie gibt, ist auf jeder Seite ablesbar, wessen Bestand
gerade offen ist.
"""

import pytest
from nicegui.testing import User

from src.core.app_home import reset_profile_cache
from src.services import import_job
from src.services.profile_service import (
    activate_profile,
    create_profile,
    rename_profile,
)

pytest_plugins = ["nicegui.testing.user_plugin"]


def _zwei_personen():
    """Aus der Einzelperson eine zweite machen — der reale Weg."""
    rename_profile("1", "Person A")
    create_profile("Person B")


@pytest.fixture(autouse=True)
def isolierte_installation(tmp_path, monkeypatch):
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

    reset_profile_cache()
    import_job._reset_for_tests()

    from src.database.init_database import init_database

    init_database()

    yield

    reset_profile_cache()
    import_job._reset_for_tests()


@pytest.mark.asyncio
async def test_ohne_zweite_person_bleibt_die_app_unveraendert(user: User):
    # Kein Name, kein Umschalter — die Zusage aus ADR 015.
    await user.open("/")
    await user.should_see("Dashboard")
    await user.should_not_see("Geöffnet:")

    await user.open("/import")
    await user.should_not_see("Importiert nach")


@pytest.mark.asyncio
async def test_das_nutzerprofil_steht_immer_in_der_seitenleiste(user: User):
    # Auch mit nur einer Person: „wessen Unterlagen sehe ich hier" soll man
    # nicht suchen müssen.
    await user.open("/")
    await user.should_see("Nutzerprofil")
    await user.should_see("Benutzer 1")

    # Zu wechseln gibt es aber noch nichts.
    await user.should_not_see("Benutzer wechseln")


@pytest.mark.asyncio
async def test_wechselknopf_erscheint_mit_der_zweiten_person(user: User):
    _zwei_personen()

    await user.open("/")
    await user.should_see("Nutzerprofil")
    await user.should_see("Person A")
    await user.should_see("Benutzer wechseln")


@pytest.mark.asyncio
async def test_einstellungen_laden_zur_zweiten_person_ein(user: User):
    await user.open("/einstellungen")
    await user.should_see("Zweite Person hinzufügen")


@pytest.mark.asyncio
async def test_zweite_person_ueber_die_einstellungen(user: User):
    """Der Einstiegspunkt des ganzen Features, über die Oberfläche."""
    from src.services.profile_service import list_profiles

    await user.open("/einstellungen")
    user.find("Zweite Person hinzufügen").click()

    assert [p["name"] for p in list_profiles()] == ["Benutzer 1", "Benutzer 2"]

    # Und ab jetzt zeigt die App überall, wer geöffnet ist.
    await user.open("/")
    await user.should_see("Geöffnet:")
    await user.should_see("Benutzer 1")


@pytest.mark.asyncio
async def test_mit_profilen_steht_der_name_auf_dem_dashboard(user: User):
    _zwei_personen()

    await user.open("/")
    await user.should_see("Geöffnet:")
    await user.should_see("Person A")


@pytest.mark.asyncio
async def test_der_name_steht_auf_jeder_seite(user: User):
    _zwei_personen()

    # Seitenleiste: gilt für alle Seiten, hier stellvertretend zwei.
    await user.open("/dokumente")
    await user.should_see("Person A")

    await user.open("/einstellungen")
    await user.should_see("Person A")


@pytest.mark.asyncio
async def test_das_importziel_steht_neben_dem_knopf(user: User):
    _zwei_personen()

    await user.open("/import")
    await user.should_see("Importiert nach Person A")


@pytest.mark.asyncio
async def test_nach_dem_wechsel_zeigt_alles_die_andere_person(user: User):
    _zwei_personen()
    activate_profile("2")

    await user.open("/")
    await user.should_see("Person B")

    await user.open("/import")
    await user.should_see("Importiert nach Person B")


@pytest.mark.asyncio
async def test_umschalten_ueber_die_seitenleiste(user: User):
    """Der ganze Klickpfad, nicht nur der Dienst darunter."""
    _zwei_personen()

    await user.open("/")
    user.find(marker="profil-wechsel-2").click()

    await user.open("/")
    await user.should_see("Person B")
    await user.should_see("Zu Person A wechseln")


@pytest.mark.asyncio
async def test_umschalten_waehrend_eines_imports_wird_abgelehnt(user: User):
    _zwei_personen()
    import_job.start()
    import_job.update_progress(12, 30, "scan.pdf")

    await user.open("/")
    user.find(marker="profil-wechsel-2").click()

    # Meldung statt Wechsel — und der Bestand bleibt, wo er war.
    await user.should_see("Stapel-Import läuft")

    await user.open("/")
    await user.should_see("Person A")


@pytest.mark.asyncio
async def test_einstellungen_listen_beide_personen(user: User):
    _zwei_personen()

    await user.open("/einstellungen")
    await user.should_see("Personen im Haushalt")
    await user.should_see("geöffnet")
    await user.should_see("Weitere Person hinzufügen")

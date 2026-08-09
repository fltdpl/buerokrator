"""Oberfläche des Umzugs aus der Zeit vor den Profilen.

Der Fall, den diese Seite abfängt, ist der stille: ohne sie zeigt die App
einem gewachsenen Bestand „0 Dokumente archiviert", weil sie im (leeren)
Profil nachsieht. Deshalb steht hier die WEICHE im Mittelpunkt, nicht die
Gestaltung — und der Nachweis, dass der Umzug über den Knopf wirklich läuft.
"""

import sqlite3

import pytest
import yaml
from nicegui.testing import User

from src.core.app_home import reset_profile_cache
from src.services import import_job

pytest_plugins = ["nicegui.testing.user_plugin"]


def _schreibe_config(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text(
        yaml.safe_dump(
            {
                "paths": {
                    "inbox": "./inbox",
                    "archive": "./archive",
                    "exports": "./exports",
                },
                "database": {"path": "./database/buerokrator.db"},
                "backup": {"target": "./backups"},
                # Der Assistent liest sie: eine frische Installation wird
                # vom Dashboard dorthin weitergeleitet.
                "classifier": {
                    "model": "gemma3:4b",
                    "temperature": 0.0,
                    "max_input_chars": 3000,
                },
                "ocr": {
                    "language": "deu+eng",
                    "tesseract": {
                        "windows": "C:/Program Files/Tesseract-OCR/tesseract.exe",
                        "linux": "/usr/bin/tesseract",
                    },
                },
                "logging": {"level": "INFO"},
                "archive": {
                    "category_mapping": {
                        "invoice": "Rechnungen",
                        "unknown": "Sonstiges",
                    }
                },
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def altbestand(tmp_path, monkeypatch):
    """Installation im Aufbau von vor ADR 015: Daten direkt in der Basis."""
    _schreibe_config(tmp_path)
    (tmp_path / ".nicegui").mkdir()

    archiv = tmp_path / "archive" / "2026" / "Rechnungen"
    archiv.mkdir(parents=True)
    beleg = archiv / "2026-01-09_Musterfirma_GmbH_Rechnung.pdf"
    beleg.write_bytes(b"%PDF-1.4 Testinhalt")

    db = tmp_path / "database" / "buerokrator.db"
    db.parent.mkdir()
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, archive_path TEXT)")
    conn.execute(
        "INSERT INTO documents (archive_path) VALUES (?)", (str(beleg),)
    )
    conn.commit()
    conn.close()

    monkeypatch.chdir(tmp_path)
    reset_profile_cache()
    import_job._reset_for_tests()

    yield tmp_path

    reset_profile_cache()
    import_job._reset_for_tests()


@pytest.fixture
def frische_installation(tmp_path, monkeypatch):
    _schreibe_config(tmp_path)
    (tmp_path / ".nicegui").mkdir()

    monkeypatch.chdir(tmp_path)
    reset_profile_cache()
    import_job._reset_for_tests()

    yield tmp_path

    reset_profile_cache()
    import_job._reset_for_tests()


@pytest.mark.asyncio
async def test_altbestand_fuehrt_auf_die_umzugsseite(altbestand, user: User):
    """Die Weiche. Ohne sie landet ein gewachsener Bestand auf einem
    Dashboard, das ihn nicht sieht."""
    await user.open("/")

    await user.should_see("Bestand aus einer älteren Version")
    await user.should_see("Umzug jetzt starten")
    await user.should_not_see("Dokumente archiviert")


@pytest.mark.asyncio
async def test_der_knopf_zieht_den_bestand_wirklich_um(altbestand, user: User):
    await user.open("/umzug")
    user.find("Umzug jetzt starten").click()

    await user.should_see("Der Umzug ist abgeschlossen.")

    # Nicht nur die Meldung: der Bestand liegt danach im Profil, die
    # Originale als Sicherung daneben, und die Datenbank zeigt auf den
    # neuen Ort.
    profil = altbestand / "profiles" / "1"
    assert (profil / "database" / "buerokrator.db").exists()
    assert (altbestand / "vor-profilen" / "database" / "buerokrator.db").exists()

    conn = sqlite3.connect(profil / "database" / "buerokrator.db")

    try:
        pfade = [row[0] for row in conn.execute("SELECT archive_path FROM documents")]

    finally:
        conn.close()

    assert pfade and all(pfad.startswith(str(profil / "archive")) for pfad in pfade)


@pytest.mark.asyncio
async def test_nach_dem_umzug_gibt_es_die_seite_nicht_mehr(altbestand, user: User):
    """Zweiter Aufruf: nichts anbieten, was nur noch schiefgehen kann."""
    await user.open("/umzug")
    user.find("Umzug jetzt starten").click()
    await user.should_see("Der Umzug ist abgeschlossen.")

    await user.open("/umzug")

    await user.should_see("Dashboard")
    await user.should_not_see("Umzug jetzt starten")


@pytest.mark.asyncio
async def test_jede_seite_fuehrt_zum_umzug_zurueck(altbestand, user: User):
    """Nicht nur das Dashboard. Jede Seite, die die Datenbank oeffnet, legt
    sonst im leeren Profil eine an — danach lehnte der Umzug ab und verlangte
    vom Nutzer, etwas zu loeschen, das die App selbst angelegt hatte.
    Gefunden im Smoke-Test des fertigen Pakets."""
    for route in ("/dokumente", "/import", "/analyse", "/einstellungen",
                  "/papierkorb"):
        await user.open(route)
        await user.should_see("Umzug jetzt starten")

    # Der eigentliche Beweis: es ist kein Profil entstanden, der Umzug
    # laeuft also noch.
    assert not (altbestand / "profiles").exists()


@pytest.mark.asyncio
async def test_frische_installation_sieht_den_umzug_nie(
    frische_installation, user: User
):
    """Ohne Bestand gehört der Einrichtungsassistent hierher, nicht der
    Umzug — sonst böte die App an, Nichts zu verschieben."""
    await user.open("/umzug")

    await user.should_not_see("Umzug jetzt starten")

"""Die Backup-Seite in den Einstellungen: Aufräumen und Profilhinweis.

Zwei Dinge, die man erst am Bestand merkt: der Platzbedarf wächst
unbegrenzt (jede Sicherung eine Vollkopie, jede Wiederherstellung legt den
alten Stand daneben), und gesichert wird immer nur die GEÖFFNETE Person —
alle Pfade sind profilaufgelöst. Beides gehört auf die Fläche, sonst merkt
es niemand.
"""

import zipfile

import pytest
import yaml
from nicegui.testing import User

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
def instanz(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
    _schreibe_config(tmp_path)

    from src.core.app_home import reset_profile_cache
    from src.database.database import reset_schema_state
    from src.database.init_database import init_database

    reset_profile_cache()
    reset_schema_state()
    init_database()

    yield tmp_path

    reset_profile_cache()
    reset_schema_state()


def _sicherungen(*zeitpunkte):
    from src.core.app_home import get_app_home

    ziel = get_app_home() / "backups"
    ziel.mkdir(parents=True, exist_ok=True)

    for zeitpunkt in zeitpunkte:
        with zipfile.ZipFile(
            ziel / f"buerokrator_backup_{zeitpunkt}.zip", "w"
        ) as archive:
            archive.writestr("database/buerokrator.db", "x" * 100)


# ------------------------------------------------------------- Aufräumen


async def test_ohne_kandidaten_steht_da_dass_nichts_zu_tun_ist(user: User, instanz):
    _sicherungen("20260701_090000")

    await user.open("/einstellungen")
    user.find(marker="tab-backup").click()

    await user.should_see(marker="aufraeumen-nichts")
    await user.should_not_see(marker="aufraeumen")


async def test_alte_sicherungen_werden_zum_aufraeumen_angeboten(user: User, instanz):
    _sicherungen(
        "20240101_090000",
        "20250101_090000",
        "20260101_090000",
        "20260401_090000",
        "20260701_090000",
    )

    await user.open("/einstellungen")
    user.find(marker="tab-backup").click()

    await user.should_see(marker="aufraeumen")
    # Die beiden ältesten jenseits der jüngsten drei. Geprüft über die
    # Zusammenfassung: die Dateinamen selbst stehen auf derselben Seite auch
    # in der Auswahl zum Wiederherstellen und belegen deshalb nichts.
    await user.should_see("2 ältere Sicherung(en) und 0 Rest(e)")


async def test_aufraeumen_verschiebt_in_den_papierkorb(user: User, instanz):
    from src.core.app_home import get_app_home

    _sicherungen(
        "20240101_090000",
        "20260101_090000",
        "20260401_090000",
        "20260701_090000",
    )

    await user.open("/einstellungen")
    user.find(marker="tab-backup").click()
    await user.should_see(marker="aufraeumen")
    user.find(marker="aufraeumen").click()

    # Die Fläche zieht nach: nichts mehr zu tun, dafür liegt etwas im
    # Papierkorb.
    await user.should_see(marker="aufraeumen-nichts")
    await user.should_see(marker="papierkorb-leeren")

    papierkorb = get_app_home() / "trash" / "sicherungen"

    assert [p.name for p in papierkorb.iterdir()] == [
        "buerokrator_backup_20240101_090000.zip"
    ]
    assert not (
        get_app_home() / "backups" / "buerokrator_backup_20240101_090000.zip"
    ).exists()


async def test_reste_einer_wiederherstellung_werden_angeboten(user: User, instanz):
    from src.core.app_home import get_app_home

    rest = get_app_home() / "archive_vor_wiederherstellung_20260101_120000"
    rest.mkdir(parents=True)
    (rest / "alt.pdf").write_bytes(b"PDF")

    await user.open("/einstellungen")
    user.find(marker="tab-backup").click()

    await user.should_see("archive_vor_wiederherstellung_20260101_120000")
    await user.should_see(marker="aufraeumen")


# ---------------------------------------------------- Hinweis auf das Profil


async def test_ohne_zweite_person_kein_hinweis(user: User, instanz):
    """Bei einer einzigen Person gibt es nichts zu verwechseln."""
    await user.open("/einstellungen")
    user.find(marker="tab-backup").click()

    await user.should_not_see(marker="backup-profil")


async def test_mit_zweiter_person_nennt_die_seite_wessen_bestand(user: User, instanz):
    """Sonst hält man die Sicherung für die des ganzen Haushalts."""
    from src.services.profile_service import create_profile

    create_profile("Person B")

    await user.open("/einstellungen")
    user.find(marker="tab-backup").click()

    await user.should_see(marker="backup-profil")

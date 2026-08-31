"""Alter der letzten Sicherung — als Aufgabe auf dem Dashboard.

Der Bestand liegt nur auf diesem Rechner. Was seit der letzten Sicherung
dazugekommen ist, ist bei einem Plattenschaden weg — das ist die einzige
Zahl des Dashboards, hinter der ein echter Verlust steht.

Als Zeile in „Aufgaben", nicht als Kachel: Kacheln zeigen Zustand, Aufgaben
verlangen eine Handlung. Und nur eine ÜBERFÄLLIGE Sicherung ist eine
Handlung — eine frische bleibt eine ruhige Zeile ohne Knopf, sonst mahnt das
Dashboard jeden Tag etwas an, das längst getan ist.

Geprüft wird gegen erfundene Sicherungen in einer isolierten Instanz, nie
gegen den echten Bestand.
"""

import os
from datetime import datetime, timedelta

import pytest
from nicegui.testing import User

import src.database.database as database
from src.services.backup_service import BACKUP_WARNUNG_TAGE

pytest_plugins = ["nicegui.testing.user_plugin"]


CONFIG = "\n".join(
    [
        "paths:",
        "  inbox: ./inbox",
        "  archive: ./archive",
        "  exports: ./exports",
        "database:",
        "  path: ./database/buerokrator.db",
        "backup:",
        "  target: ./backups",
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
)


@pytest.fixture(autouse=True)
def isolierte_instanz(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(CONFIG, encoding="utf-8")
    (tmp_path / ".nicegui").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(database, "_schema_ready", False)

    from src.database.init_database import init_database

    init_database()

    return tmp_path


def _sicherung(name, alter_tage):
    """Legt eine erfundene Backup-ZIP mit gewähltem Alter im Zielordner an."""
    from src.core.app_home import get_app_home

    ziel = get_app_home() / "backups"
    ziel.mkdir(parents=True, exist_ok=True)

    datei = ziel / name
    datei.write_bytes(b"PK")

    zeitpunkt = (datetime.now() - timedelta(days=alter_tage)).timestamp()
    os.utime(datei, (zeitpunkt, zeitpunkt))

    return datei


def _dokument(verified=1):
    from src.database.database import get_connection

    conn = get_connection()
    conn.execute(
        "INSERT INTO documents (filename, document_type, verified)"
        " VALUES ('muster.pdf', 'invoice', ?)",
        (verified,),
    )
    conn.commit()
    conn.close()


# --------------------------------------------------------------- das Alter


def test_list_backups_nennt_den_zeitpunkt(tmp_path):
    from src.services.backup_service import list_backups

    ziel = tmp_path / "backups"
    ziel.mkdir()
    (ziel / "b.zip").write_bytes(b"PK")

    eintrag = list_backups(ziel)[0]

    assert eintrag["mtime"] == pytest.approx((ziel / "b.zip").stat().st_mtime)


def test_ohne_sicherung_ist_das_alter_unbekannt(tmp_path):
    """Kein Backup ist NICHT „0 Tage alt" — der Unterschied trägt die
    Beschriftung („Noch keine Sicherung" statt „heute")."""
    from src.services.backup_service import backup_alter_tage

    assert backup_alter_tage(tmp_path / "fehlt") is None
    (tmp_path / "leer").mkdir()
    assert backup_alter_tage(tmp_path / "leer") is None


def test_alter_zaehlt_angefangene_tage_nicht_mit():
    """Angefangene Tage runden ab: „vor 3 Tagen" darf nicht schon nach
    zweieinhalb dastehen."""
    from src.core.app_home import get_app_home
    from src.services.backup_service import backup_alter_tage

    _sicherung("b.zip", alter_tage=3.5)

    assert backup_alter_tage(get_app_home() / "backups") == 3


def test_alter_nimmt_die_juengste_sicherung():
    from src.core.app_home import get_app_home
    from src.services.backup_service import backup_alter_tage

    _sicherung("alt.zip", alter_tage=40)
    _sicherung("neu.zip", alter_tage=1)

    assert backup_alter_tage(get_app_home() / "backups") == 1


def test_alter_verlaesst_sich_nicht_auf_die_uhr():
    """Eine Sicherung aus der Zukunft (verstellte Uhr, kopierte Datei) darf
    kein negatives Alter ergeben — „vor -2 Tagen" wäre Unsinn."""
    from src.core.app_home import get_app_home
    from src.services.backup_service import backup_alter_tage

    _sicherung("b.zip", alter_tage=-2)

    assert backup_alter_tage(get_app_home() / "backups") == 0


def test_backup_ziel_kommt_aus_der_konfiguration():
    from src.core.app_home import get_app_home
    from src.services.backup_service import backup_ziel

    assert backup_ziel() == str(get_app_home() / "backups")


# ------------------------------------------------------- Zeile im Dashboard


@pytest.mark.asyncio
async def test_dashboard_nennt_das_alter_der_letzten_sicherung(user: User):
    _sicherung("b.zip", alter_tage=3)

    await user.open("/")

    await user.should_see("Letztes Backup vor 3 Tagen")


@pytest.mark.asyncio
async def test_dashboard_schreibt_die_einzahl_richtig(user: User):
    _sicherung("b.zip", alter_tage=1)

    await user.open("/")

    await user.should_see("Letztes Backup vor 1 Tag")


@pytest.mark.asyncio
async def test_sicherung_von_heute_heisst_heute(user: User):
    """„vor 0 Tagen" liest sich wie ein Fehler in der Anwendung."""
    _sicherung("b.zip", alter_tage=0)

    await user.open("/")

    await user.should_see("Letztes Backup heute")


@pytest.mark.asyncio
async def test_frische_sicherung_ist_keine_aufgabe(user: User):
    _sicherung("b.zip", alter_tage=BACKUP_WARNUNG_TAGE - 1)

    await user.open("/")

    await user.should_not_see(marker="backup-jetzt")


@pytest.mark.asyncio
async def test_alte_sicherung_wird_zur_aufgabe(user: User):
    _sicherung("b.zip", alter_tage=BACKUP_WARNUNG_TAGE)

    await user.open("/")

    await user.should_see(marker="backup-jetzt")


@pytest.mark.asyncio
async def test_ohne_sicherung_steht_die_aufgabe_da(user: User):
    """Der gefährlichste Fall: es gab nie eine."""
    await user.open("/")

    await user.should_see("Noch keine Sicherung")
    await user.should_see(marker="backup-jetzt")


@pytest.mark.asyncio
async def test_faellige_sicherung_widerspricht_der_entwarnung(user: User):
    """„Keine offenen Aufgaben" darf nicht über einer offenen Aufgabe stehen."""
    _dokument(verified=1)

    await user.open("/")

    await user.should_see(marker="backup-jetzt")
    await user.should_not_see("Keine offenen Aufgaben")


@pytest.mark.asyncio
async def test_entwarnung_bleibt_wenn_auch_die_sicherung_frisch_ist(user: User):
    _dokument(verified=1)
    _sicherung("b.zip", alter_tage=0)

    await user.open("/")

    await user.should_see("Keine offenen Aufgaben")


@pytest.mark.asyncio
async def test_knopf_erstellt_die_sicherung_und_zieht_die_zeile_nach(user: User):
    """Bliebe die Warnung nach dem Klick stehen, sähe der Knopf wirkungslos aus."""
    from src.core.app_home import get_app_home

    await user.open("/")
    user.find(marker="backup-jetzt").click()

    await user.should_see("Letztes Backup heute")

    assert list((get_app_home() / "backups").glob("*.zip"))

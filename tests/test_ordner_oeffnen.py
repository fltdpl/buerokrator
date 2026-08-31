"""Backup-Ordner im Dateimanager des Betriebssystems öffnen.

Die Sicherungen sind das einzige, was der Nutzer von Hand anfasst — auf einen
Stick kopieren, an einen anderen Ort legen, eine alte löschen. Bisher nannte
die Backup-Seite den Pfad nur als Text; ihn abzutippen ist der lange Weg zu
einem Ordner, den die App genau kennt.

Geöffnet wird SERVERSEITIG: Oberfläche und Bestand liegen auf demselben
Rechner (localhost, Einzelplatz — dieselbe Voraussetzung wie bei `/pdf/{id}`).
Ein Browser könnte einen lokalen Ordner ohnehin nicht öffnen.

Die Plattformweiche wird in beide Richtungen geprüft: das Windows-Paket ist
erklärtes Ziel, und ein `xdg-open` auf Windows fiele erst dort auf.
"""

import os
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml
from nicegui.testing import User

from src.services import file_manager
from src.services.file_manager import oeffne_ordner

pytest_plugins = ["nicegui.testing.user_plugin"]


# ------------------------------------------------------------- die Weiche


def _plattform(monkeypatch, name, startfile=None):
    """Stellt die Weiche, ohne das echte `os.name` anzufassen.

    ⚠️ Global gesetzt ändert `os.name` auch pathlib: `Path()` liefert dann
    einen WindowsPath, und schon `is_dir()` prüft einen mit Backslashes
    umgeschriebenen Pfad — der Test scheiterte an seiner eigenen Kulisse.
    Deshalb wird nur das `os` DIESES Moduls ersetzt.
    """
    # `environ` ist bewusst das echte Objekt: so wirken `monkeypatch.setenv`
    # und `delenv` auch durch den Ersatz hindurch.
    ersatz = SimpleNamespace(name=name, environ=os.environ)

    if startfile is not None:
        ersatz.startfile = startfile

    monkeypatch.setattr(file_manager, "os", ersatz)


def test_linux_ruft_xdg_open(tmp_path, monkeypatch):
    aufrufe = []

    _plattform(monkeypatch, "posix")
    monkeypatch.setattr(
        subprocess, "Popen", lambda befehl, **rest: aufrufe.append(befehl)
    )

    oeffne_ordner(tmp_path)

    assert aufrufe == [["xdg-open", str(tmp_path)]]


def test_linux_wartet_nicht_auf_den_dateimanager(tmp_path, monkeypatch):
    """`Popen`, nicht `run`: manche Dateimanager kehren erst zurück, wenn ihr
    Fenster geschlossen wird — die Oberfläche stünde so lange still."""
    _plattform(monkeypatch, "posix")
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: pytest.fail("darf nicht warten")
    )
    monkeypatch.setattr(subprocess, "Popen", lambda befehl, **rest: None)

    oeffne_ordner(tmp_path)


def test_windows_nutzt_den_explorer(tmp_path, monkeypatch):
    aufrufe = []

    _plattform(monkeypatch, "nt", startfile=aufrufe.append)
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("kein xdg-open auf Windows")
    )

    oeffne_ordner(tmp_path)

    assert aufrufe == [str(tmp_path)]


# ------------------------------------------------- Umgebung des Release-Pakets


def _umgebung_beim_oeffnen(tmp_path, monkeypatch):
    """Startet das Öffnen und gibt die Umgebung zurück, die xdg-open bekäme."""
    mitgeschrieben = {}

    _plattform(monkeypatch, "posix")
    monkeypatch.setattr(
        subprocess, "Popen", lambda befehl, **rest: mitgeschrieben.update(rest["env"])
    )

    oeffne_ordner(tmp_path)

    return mitgeschrieben


def test_paket_gibt_seine_bibliothekspfade_nicht_weiter(tmp_path, monkeypatch):
    """Sonst lädt xdg-open unsere gebündelten Bibliotheken statt der eigenen
    und bricht ab — und zwar nur im Release-Paket, nie in der Entwicklung."""
    monkeypatch.setenv("LD_LIBRARY_PATH", "/paket/_internal")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/eigenes/lib")

    umgebung = _umgebung_beim_oeffnen(tmp_path, monkeypatch)

    assert umgebung["LD_LIBRARY_PATH"] == "/eigenes/lib"
    assert "LD_LIBRARY_PATH_ORIG" not in umgebung


def test_ohne_vorherigen_wert_faellt_der_pfad_ganz_weg(tmp_path, monkeypatch):
    """Der Normalfall: die Variable war vor dem Start gar nicht gesetzt, der
    Bootloader hinterlässt deshalb auch kein Original."""
    monkeypatch.setenv("LD_LIBRARY_PATH", "/paket/_internal")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert "LD_LIBRARY_PATH" not in _umgebung_beim_oeffnen(tmp_path, monkeypatch)


def test_ausserhalb_des_pakets_bleibt_die_umgebung_unberuehrt(tmp_path, monkeypatch):
    """In der Entwicklung ist ein gesetzter Wert der des Nutzers."""
    monkeypatch.setenv("LD_LIBRARY_PATH", "/eigenes/lib")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)

    umgebung = _umgebung_beim_oeffnen(tmp_path, monkeypatch)

    assert umgebung["LD_LIBRARY_PATH"] == "/eigenes/lib"


# ------------------------------------------------------------- die Fehler


def test_fehlender_ordner_wird_gemeldet(tmp_path):
    """Vor der ersten Sicherung gibt es den Ordner noch nicht. Er wird hier
    NICHT angelegt: „Öffnen" darf nichts erschaffen."""
    fehlt = tmp_path / "backups"

    with pytest.raises(FileNotFoundError) as fehler:
        oeffne_ordner(fehlt)

    assert str(fehlt) in str(fehler.value)
    assert not fehlt.exists()


def test_datei_ist_kein_ordner(tmp_path):
    datei = tmp_path / "b.zip"
    datei.write_bytes(b"PK")

    with pytest.raises(FileNotFoundError):
        oeffne_ordner(datei)


def test_fehlender_dateimanager_wird_erklaert(tmp_path, monkeypatch):
    """Ohne Übersetzung stünde „No such file or directory: 'xdg-open'" in der
    Meldung — der Nutzer suchte dann den Fehler bei seinem Ordner."""

    def kein_xdg_open(*a, **k):
        raise FileNotFoundError(2, "No such file or directory", "xdg-open")

    _plattform(monkeypatch, "posix")
    monkeypatch.setattr(subprocess, "Popen", kein_xdg_open)

    with pytest.raises(RuntimeError) as fehler:
        oeffne_ordner(tmp_path)

    assert "Dateimanager" in str(fehler.value)


# --------------------------------------------------- Knopf in den Einstellungen


@pytest.fixture
def instanz(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
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

    from src.core.app_home import reset_profile_cache
    from src.database.database import reset_schema_state
    from src.database.init_database import init_database

    reset_profile_cache()
    reset_schema_state()
    init_database()

    yield tmp_path

    reset_profile_cache()
    reset_schema_state()


async def test_backup_seite_oeffnet_den_zielordner(user: User, instanz, monkeypatch):
    from src.core.app_home import get_app_home
    from src.frontend.pages import settings

    ziel = get_app_home() / "backups"
    ziel.mkdir(parents=True)

    geoeffnet = []
    monkeypatch.setattr(settings, "oeffne_ordner", geoeffnet.append)

    await user.open("/einstellungen")
    # Über den Marker, nicht über den Text: "Backup" träfe auch die
    # Beschriftungen im Panel — darunter den Knopf, der wirklich sichert.
    user.find(marker="tab-backup").click()
    await user.should_see(marker="backup-ordner")
    user.find(marker="backup-ordner").click()

    assert geoeffnet == [str(ziel)]


async def test_fehler_beim_oeffnen_bleibt_beim_nutzer(user: User, instanz, monkeypatch):
    """Ein fehlender Ordner darf keine Ausnahme in die Oberfläche werfen."""
    from src.frontend.pages import settings

    def scheitert(_pfad):
        raise FileNotFoundError("Ordner gibt es nicht")

    monkeypatch.setattr(settings, "oeffne_ordner", scheitert)

    await user.open("/einstellungen")
    # Über den Marker, nicht über den Text: "Backup" träfe auch die
    # Beschriftungen im Panel — darunter den Knopf, der wirklich sichert.
    user.find(marker="tab-backup").click()
    user.find(marker="backup-ordner").click()

    await user.should_see("Ordner gibt es nicht")

"""Auflösung der beiden Wurzeln (cwd-Entkopplung, Profilebene, ADR 015).

`get_base_home()` ist die Installation (Einstellungen, Log), `get_app_home()`
der Datenbestand des aktiven Profils. Beide fallen nie zusammen: Daten liegen
**immer** unter `profiles/<kennung>/`, auch bei einer einzigen Person.
"""

from pathlib import Path

import pytest

from src.core.app_home import (
    DEFAULT_PROFILE,
    get_app_home,
    get_base_home,
    reset_profile_cache,
    resolve_path,
)
from src.core.config import config_path, load_config, save_config


@pytest.fixture(autouse=True)
def sauberer_profil_cache():
    reset_profile_cache()
    yield
    reset_profile_cache()


def _write_config(base):
    config_dir = base / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                "  inbox: ./inbox",
                "  archive: ./archive",
                "  exports: ./exports",
                "database:",
                "  path: ./database/test.db",
                "backup:",
                "  target: /absoluter/backup/ort",
            ]
        ),
        encoding="utf-8",
    )


def _standardprofil(base):
    return base / "profiles" / DEFAULT_PROFILE


def test_env_variable_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path / "daheim"))

    assert get_base_home() == tmp_path / "daheim"


def test_cwd_mode_when_config_exists(tmp_path, monkeypatch):
    monkeypatch.delenv("BUEROKRATOR_HOME", raising=False)
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert get_base_home() == Path.cwd()


def test_user_data_dir_fallback(tmp_path, monkeypatch):
    # Kein Env-Override, keine Config im cwd -> Benutzer-Datenverzeichnis.
    monkeypatch.delenv("BUEROKRATOR_HOME", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    empty = tmp_path / "leer"
    empty.mkdir()
    monkeypatch.chdir(empty)

    assert get_base_home() == tmp_path / "xdg" / "buerokrator"


def test_daten_liegen_immer_im_profil(tmp_path, monkeypatch):
    # Auch ohne profiles.yaml: eine Installation hat genau eine Struktur.
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    assert get_app_home() == _standardprofil(tmp_path)
    assert get_app_home() != get_base_home()


def test_resolve_path_keeps_absolute(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    assert resolve_path("/etc/anderswo") == Path("/etc/anderswo")
    assert resolve_path("./archive") == _standardprofil(tmp_path) / "archive"


def test_load_config_absolutizes_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("BUEROKRATOR_HOME", raising=False)
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    config = load_config()
    profil = _standardprofil(tmp_path)

    # Die Einstellungen sind gemeinsam, ihre relativen Pfade lösen aber
    # gegen das PROFIL auf — dadurch bekommt jede Person ihr eigenes Archiv,
    # ohne dass die Config etwas davon wüsste.
    assert config["paths"]["archive"] == str(profil / "archive")
    assert config["database"]["path"] == str(profil / "database" / "test.db")
    # Absolute Werte bleiben unangetastet (und wären für alle dieselben).
    assert config["backup"]["target"] == "/absoluter/backup/ort"


def test_settings_bleiben_in_der_basis(tmp_path, monkeypatch):
    monkeypatch.delenv("BUEROKRATOR_HOME", raising=False)
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert config_path() == tmp_path / "config" / "settings.yaml"


def test_save_config_relativizes_paths_inside_home(tmp_path, monkeypatch):
    monkeypatch.delenv("BUEROKRATOR_HOME", raising=False)
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    config = load_config()
    save_config(config)

    raw = config_path().read_text(encoding="utf-8")
    profil = _standardprofil(tmp_path)

    # Innerhalb des Profils: wieder relativ (portable YAML) ...
    assert "./archive" in raw
    assert str(profil / "archive") not in raw
    # ... außerhalb: absolut erhalten.
    assert "/absoluter/backup/ort" in raw
    # Round-trip: erneutes Laden liefert wieder dieselben absoluten Pfade.
    assert load_config()["paths"]["archive"] == str(profil / "archive")


def test_first_run_copies_template_config(tmp_path, monkeypatch):
    # Leeres Home (installierte App, erster Start): die mitgelieferte
    # config/settings.yaml wird als Standard-Config kopiert.
    home = tmp_path / "frisch"
    monkeypatch.setenv("BUEROKRATOR_HOME", str(home))

    config = load_config()

    assert (home / "config" / "settings.yaml").exists()
    # Vorlage ist die echte Projekt-Config: Kernschlüssel vorhanden,
    # Pfade gegen das Standardprofil aufgelöst.
    assert config["paths"]["archive"] == str(_standardprofil(home) / "archive")
    assert "supported_document_types" in config


# --------------------------------------------------- Archivpfade auflösen


def test_resolve_archive_path_macht_relative_pfade_absolut(tmp_path, monkeypatch):
    """Ältere Importe hinterließen relative Pfade in archive_path.

    Roh ausgewertet lösen sie gegen das ARBEITSVERZEICHNIS auf — die
    Existenzprüfung war damit zufällig, je nachdem, wo der Prozess stand.
    Gemeint sind sie gegen das App-Home.
    """
    from src.core.app_home import resolve_archive_path

    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    aufgeloest = resolve_archive_path("archive/2024/Wohnen/miete.pdf")

    assert aufgeloest.is_absolute()
    assert aufgeloest == (
        tmp_path / "profiles" / "1" / "archive" / "2024" / "Wohnen" / "miete.pdf"
    )


def test_resolve_archive_path_laesst_absolute_pfade_stehen(tmp_path, monkeypatch):
    from src.core.app_home import resolve_archive_path

    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
    absolut = tmp_path / "anderswo" / "miete.pdf"

    assert resolve_archive_path(str(absolut)) == absolut


def test_resolve_archive_path_leer_bleibt_none(tmp_path, monkeypatch):
    """Ein leerer Wert darf NIE zum App-Home werden — das Verzeichnis
    existiert, und exists() meldete dann fälschlich eine vorhandene Datei."""
    from src.core.app_home import resolve_archive_path

    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    assert resolve_archive_path("") is None
    assert resolve_archive_path(None) is None

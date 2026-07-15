"""App-Home-Auflösung (cwd-Entkopplung, Vorbereitung Installer-Fähigkeit)."""

from pathlib import Path

from src.core.app_home import get_app_home, resolve_path
from src.core.config import config_path, load_config, save_config


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


def test_env_variable_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path / "daheim"))

    assert get_app_home() == tmp_path / "daheim"


def test_cwd_mode_when_config_exists(tmp_path, monkeypatch):
    monkeypatch.delenv("BUEROKRATOR_HOME", raising=False)
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert get_app_home() == Path.cwd()


def test_user_data_dir_fallback(tmp_path, monkeypatch):
    # Kein Env-Override, keine Config im cwd -> Benutzer-Datenverzeichnis.
    monkeypatch.delenv("BUEROKRATOR_HOME", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    empty = tmp_path / "leer"
    empty.mkdir()
    monkeypatch.chdir(empty)

    assert get_app_home() == tmp_path / "xdg" / "buerokrator"


def test_resolve_path_keeps_absolute(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    assert resolve_path("/etc/anderswo") == Path("/etc/anderswo")
    assert resolve_path("./archive") == tmp_path / "archive"


def test_load_config_absolutizes_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("BUEROKRATOR_HOME", raising=False)
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    config = load_config()

    assert config["paths"]["archive"] == str(tmp_path / "archive")
    assert config["database"]["path"] == str(tmp_path / "database" / "test.db")
    # Absolute Werte bleiben unangetastet.
    assert config["backup"]["target"] == "/absoluter/backup/ort"


def test_save_config_relativizes_paths_inside_home(tmp_path, monkeypatch):
    monkeypatch.delenv("BUEROKRATOR_HOME", raising=False)
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    config = load_config()
    save_config(config)

    raw = config_path().read_text(encoding="utf-8")

    # Innerhalb des Homes: wieder relativ (portable YAML) ...
    assert "./archive" in raw
    assert str(tmp_path / "archive") not in raw
    # ... außerhalb: absolut erhalten.
    assert "/absoluter/backup/ort" in raw
    # Round-trip: erneutes Laden liefert wieder dieselben absoluten Pfade.
    assert load_config()["paths"]["archive"] == str(tmp_path / "archive")


def test_first_run_copies_template_config(tmp_path, monkeypatch):
    # Leeres Home (installierte App, erster Start): die mitgelieferte
    # config/settings.yaml wird als Standard-Config kopiert.
    home = tmp_path / "frisch"
    monkeypatch.setenv("BUEROKRATOR_HOME", str(home))

    config = load_config()

    assert (home / "config" / "settings.yaml").exists()
    # Vorlage ist die echte Projekt-Config: Kernschlüssel vorhanden,
    # Pfade gegen das neue Home aufgelöst.
    assert config["paths"]["archive"] == str(home / "archive")
    assert "supported_document_types" in config

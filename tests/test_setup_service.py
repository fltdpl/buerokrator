"""Tests für den First-Run-Assistenten (setup_service): wann er nötig ist,
Marker-Abschluss, Installationshinweise."""

import src.services.setup_service as setup
from src.database.init_database import init_database


def write_config(tmp_path):
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
            ]
        ),
        encoding="utf-8",
    )


def test_fresh_instance_needs_setup(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert setup.needs_setup() is True


def test_existing_database_skips_setup(tmp_path, monkeypatch):
    # Bestandsinstallation von vor dem Assistenten: DB da, kein Marker.
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    init_database()

    assert setup.needs_setup() is False


def test_complete_setup_writes_marker(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    setup.complete_setup()

    assert (tmp_path / ".setup_done").exists()
    assert setup.needs_setup() is False


def test_setup_checks_add_hints_for_missing(tmp_path, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    fake_status = [
        {"name": "Ollama", "ok": False, "detail": "nicht erreichbar"},
        {"name": "Modell „gemma3:4b“", "ok": False, "detail": "fehlt"},
        {"name": "Tesseract OCR", "ok": True, "detail": "v5"},
        {"name": "PDF-Renderer (pypdfium2)", "ok": True, "detail": "ok"},
    ]
    monkeypatch.setattr(
        setup, "collect_dependency_status", lambda config: fake_status
    )

    checks = setup.setup_checks()

    assert checks[0]["hint"].startswith("curl -fsSL https://ollama.com")
    assert checks[1]["hint"] == "ollama pull gemma3:4b"
    assert setup.all_checks_ok(checks) is False

    all_ok = [{**check, "ok": True} for check in checks]
    assert setup.all_checks_ok(all_ok) is True

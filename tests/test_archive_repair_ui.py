"""Archivpfad-Reparatur in den Einstellungen.

Der Fall, den diese Fläche abfängt, ist still: nach einer Wiederherstellung
an einem anderen Ort liegen alle Dateien richtig, aber jede Detailansicht
meldet "PDF-Datei nicht gefunden". Wer nur ein Werkzeug in `tools/` anbietet,
hilft genau der betroffenen Gruppe nicht — ein Release-Paket hat weder
Python noch `tools/` (dieselbe Lehre wie beim Umzug in 0.3.0).
"""

import json
import sqlite3

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
def instanz_mit_verirrtem_pfad(tmp_path, monkeypatch):
    """Ein Bestand, dessen einzige Zeile auf einen fremden Ort zeigt."""
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
    _schreibe_config(tmp_path)

    from src.core.app_home import reset_profile_cache
    from src.database.database import reset_schema_state
    from src.database.init_database import init_database

    reset_profile_cache()
    reset_schema_state()

    profil = tmp_path / "profiles" / "1"
    archiv = profil / "archive" / "2024" / "Rechnungen"
    archiv.mkdir(parents=True)
    (archiv / "rechnung.pdf").write_bytes(b"PDF")

    init_database()

    db = profil / "database" / "buerokrator.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        INSERT INTO documents (filename, archive_path, document_type,
                               extracted_data, verified)
        VALUES (?, ?, ?, ?, 0)
        """,
        (
            "rechnung.pdf",
            "/ganz/woanders/archive/2024/Rechnungen/rechnung.pdf",
            "invoice",
            json.dumps({}),
        ),
    )
    conn.commit()
    conn.close()

    yield {"db": db, "archiv": profil / "archive"}

    reset_profile_cache()
    reset_schema_state()


def _pfad(db):
    conn = sqlite3.connect(db)

    try:
        return conn.execute("SELECT archive_path FROM documents").fetchone()[0]

    finally:
        conn.close()


async def test_einstellungen_melden_verirrte_pfade(
    user: User, instanz_mit_verirrtem_pfad
):
    await user.open("/einstellungen")
    user.find("Datenbank").click()
    await user.should_see(marker="archivpfade-befund")


async def test_reparatur_bindet_die_datei_neu(user: User, instanz_mit_verirrtem_pfad):
    await user.open("/einstellungen")
    user.find("Datenbank").click()
    await user.should_see(marker="archivpfade-reparieren")
    user.find(marker="archivpfade-reparieren").click()
    await user.should_see("repariert")

    # Speicherform seit Schema v7: relativ zum App-Home, damit der Bestand
    # den nächsten Ortswechsel ohne Reparatur übersteht.
    assert _pfad(instanz_mit_verirrtem_pfad["db"]) == "archive/2024/Rechnungen/rechnung.pdf"


async def test_pdf_route_findet_datei_hinter_relativem_pfad(
    user: User, instanz_mit_verirrtem_pfad
):
    """Regression: `Path(archive_path)` loeste relative Werte gegen die cwd auf.

    Aeltere Importe haben solche Werte hinterlassen. Gemeint sind sie gegen
    das App-Home — dort liegt die Datei auch.
    """
    from src.frontend.main import serve_pdf

    db = instanz_mit_verirrtem_pfad["db"]
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE documents SET archive_path = ?",
        ("archive/2024/Rechnungen/rechnung.pdf",),
    )
    conn.commit()
    conn.close()

    antwort = serve_pdf(1)

    assert str(antwort.path) == str(
        instanz_mit_verirrtem_pfad["archiv"] / "2024/Rechnungen/rechnung.pdf"
    )


async def test_pdf_route_nennt_die_reparatur(user: User, instanz_mit_verirrtem_pfad):
    """Ein blankes „nicht gefunden“ liess den Nutzer ohne naechsten Schritt."""
    from fastapi import HTTPException

    from src.frontend.main import serve_pdf

    db = instanz_mit_verirrtem_pfad["db"]
    conn = sqlite3.connect(db)
    conn.execute("UPDATE documents SET archive_path = ?", ("/weg/weg/weg/x.pdf",))
    conn.commit()
    conn.close()

    with pytest.raises(HTTPException) as fehler:
        serve_pdf(1)

    assert fehler.value.status_code == 404
    assert "Archivpfade" in fehler.value.detail

"""Kennzahlen aus der Datenbank.

Hintergrund: get_verification_statistics lieferte ein Dict {0: n, 1: m}.
Die Aufrufer entpackten es (`unverified, verified = ...`) und bekamen damit
die SCHLÜSSEL 0 und 1 statt der Anzahlen — das Dashboard zeigte dauerhaft
"0 ungeprüft · 1 geprüft", egal wie viele Dokumente eingelesen waren.
"""

import src.database.database as database
from src.database.database import get_connection
from src.database.statistics import get_verification_statistics
from src.services.stats_service import get_dashboard_data


def _setup_db(tmp_path, monkeypatch, verified_count, unverified_count):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "database:",
                f"  path: {tmp_path / 'database' / 'test.db'}",
                "paths:",
                f"  inbox: {tmp_path / 'inbox'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    # Die Schema-Migration läuft nur einmal pro Prozess; für eine frische
    # Testdatenbank muss das Flag zurück.
    monkeypatch.setattr(database, "_schema_ready", False)

    conn = get_connection()
    for verified, count in ((1, verified_count), (0, unverified_count)):
        for _ in range(count):
            conn.execute(
                "INSERT INTO documents (filename, document_type, verified)"
                " VALUES (?, ?, ?)",
                ("egal.pdf", "invoice", verified),
            )
    conn.commit()
    conn.close()


def test_verification_statistics_liefert_anzahlen_nicht_schluessel(
    tmp_path, monkeypatch
):
    _setup_db(tmp_path, monkeypatch, verified_count=133, unverified_count=4)

    assert get_verification_statistics() == (4, 133)


def test_dashboard_zaehlt_geprueft_und_ungeprueft(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch, verified_count=3, unverified_count=2)

    data = get_dashboard_data()

    assert data["verified_count"] == 3
    assert data["unverified_count"] == 2
    assert data["total"] == 5

"""`archive_path` relativ speichern — der Bestand überlebt jeden Ortswechsel.

Bisher stand der Pfad absolut in der Datenbank. Das war die Ursache eines
realen Fehlerfalls: eine Sicherung, an einem anderen Ort eingespielt, ließ
jedes Altdokument ins Leere zeigen — alle Datenbankwerte richtig, nur die
Datei "nicht gefunden". Die Reparatur heilt so etwas, verhindert es aber
nicht.

Relativ zum **App-Home** gespeichert (nicht zum Archiv-Root) verschiebt sich
der Bezugspunkt mit dem Bestand: `resolve_archive_path` löst schon heute
gegen das App-Home auf, alle Leser bleiben also unverändert. Dieselbe Regel
gilt in `config.save_config` für die Pfadwerte der Einstellungen — eine
Konvention statt zweier.
"""

import shutil
import sqlite3
from pathlib import Path

from src.core.app_home import resolve_archive_path, store_archive_path
from src.database.document_repository import insert_document, save_document
from src.database.init_database import SCHEMA_VERSION, init_database


def richte_ein(base):
    """Minimale Installation unter `base`: Config, Archiv, leeres Profil."""
    config_dir = base / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                "  archive: ./archive",
                "database:",
                "  path: ./database/buerokrator.db",
                "archive:",
                "  category_mapping:",
                "    invoice: Rechnungen",
            ]
        ),
        encoding="utf-8",
    )

    return base / "profiles" / "1"


def lege_ab(archiv, jahr, kategorie, name):
    ziel = archiv / jahr / kategorie / name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(b"%PDF-1.4 Testdatei")

    return ziel


def roher_pfad(db_path, document_id=1):
    """Der Wert, wie er WIRKLICH in der Spalte steht — ungefiltert."""
    conn = sqlite3.connect(db_path)

    try:
        row = conn.execute(
            "SELECT archive_path FROM documents WHERE id = ?", (document_id,)
        ).fetchone()

    finally:
        conn.close()

    return row[0]


# ------------------------------------------------------- die Speicherform


def test_store_archive_path_relativiert_innerhalb_des_app_home(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    absolut = tmp_path / "profiles" / "1" / "archive" / "2024" / "Wohnen" / "m.pdf"

    assert store_archive_path(absolut) == str(
        Path("archive") / "2024" / "Wohnen" / "m.pdf"
    )


def test_store_archive_path_laesst_fremde_orte_absolut(tmp_path, monkeypatch):
    """Ein bewusst außerhalb gewähltes Archiv darf nicht verbogen werden.

    Relativ gespeichert zeigte es nach dem nächsten Ortswechsel des App-Home
    an eine Stelle, an der nie eine Datei lag.
    """
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    fremd = tmp_path.parent / "extern" / "archiv" / "2024" / "Wohnen" / "m.pdf"

    assert store_archive_path(fremd) == str(fremd)


def test_store_archive_path_leer_bleibt_leer(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    assert store_archive_path("") == ""
    assert store_archive_path(None) == ""


def test_store_archive_path_ist_die_umkehrung_von_resolve(tmp_path, monkeypatch):
    """Beide Richtungen gehören zusammen — sonst driften sie auseinander."""
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    absolut = tmp_path / "profiles" / "1" / "archive" / "2024" / "Wohnen" / "m.pdf"

    assert resolve_archive_path(store_archive_path(absolut)) == absolut

    # Und schon relative Werte bleiben unverändert (idempotent).
    gespeichert = store_archive_path(absolut)

    assert store_archive_path(gespeichert) == gespeichert


# --------------------------------------------------------- die Schreiber


def test_insert_document_speichert_relativ(tmp_path, monkeypatch):
    home = richte_ein(tmp_path)
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
    init_database()

    datei = lege_ab(home / "archive", "2024", "Rechnungen", "rechnung.pdf")

    document_id = insert_document(
        filename=datei.name,
        archive_path=str(datei),
        document_type="invoice",
        extracted_data={"issuer": "Musterfirma GmbH"},
    )

    db_path = home / "database" / "buerokrator.db"

    assert roher_pfad(db_path, document_id) == str(
        Path("archive") / "2024" / "Rechnungen" / "rechnung.pdf"
    )


def test_save_document_speichert_relativ(tmp_path, monkeypatch):
    home = richte_ein(tmp_path)
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
    init_database()

    datei = lege_ab(home / "archive", "2024", "Rechnungen", "rechnung.pdf")

    document_id = insert_document(
        filename=datei.name,
        archive_path=str(datei),
        document_type="invoice",
        extracted_data={"issuer": "Musterfirma GmbH"},
    )

    save_document(
        document_id=document_id,
        archive_path=str(datei),
        document_type="invoice",
        extracted_data={
            "issuer": "Musterfirma GmbH",
            "document_date": "15.03.2024",
            "amount": 42.0,
        },
    )

    db_path = home / "database" / "buerokrator.db"
    gespeichert = roher_pfad(db_path, document_id)

    assert not gespeichert.startswith(str(tmp_path))
    assert gespeichert.startswith(str(Path("archive") / "2024" / "Rechnungen"))
    # Und die Datei liegt wirklich dort, wo der Wert hinzeigt.
    assert resolve_archive_path(gespeichert).exists()


# ----------------------------------------------------------- die Migration


def test_migration_relativiert_bestandspfade(tmp_path, monkeypatch):
    home = richte_ein(tmp_path)
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
    init_database()

    datei = lege_ab(home / "archive", "2024", "Rechnungen", "rechnung.pdf")
    db_path = home / "database" / "buerokrator.db"

    # Ein Bestand aus v6: absoluter Pfad, älterer Schemastand.
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO documents (id, filename, archive_path) VALUES (1, ?, ?)",
        (datei.name, str(datei)),
    )
    conn.execute("PRAGMA user_version = 6")
    conn.commit()
    conn.close()

    init_database()

    assert roher_pfad(db_path) == str(
        Path("archive") / "2024" / "Rechnungen" / "rechnung.pdf"
    )


def test_migration_laesst_fremde_und_leere_pfade_unberuehrt(tmp_path, monkeypatch):
    home = richte_ein(tmp_path)
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
    init_database()

    fremd = "/woanders/archive/2024/Wohnen/miete.pdf"
    db_path = home / "database" / "buerokrator.db"

    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO documents (id, archive_path) VALUES (?, ?)",
        [(1, fremd), (2, ""), (3, None)],
    )
    conn.execute("PRAGMA user_version = 6")
    conn.commit()
    conn.close()

    init_database()

    assert roher_pfad(db_path, 1) == fremd
    assert roher_pfad(db_path, 2) == ""
    assert roher_pfad(db_path, 3) is None


def test_migration_hebt_den_schemastand(tmp_path, monkeypatch):
    """v7 ist der Stand, ab dem Pfade relativ liegen."""
    home = richte_ein(tmp_path)
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
    init_database()

    db_path = home / "database" / "buerokrator.db"
    conn = sqlite3.connect(db_path)

    try:
        stand = conn.execute("PRAGMA user_version").fetchone()[0]

    finally:
        conn.close()

    assert stand == SCHEMA_VERSION
    assert SCHEMA_VERSION >= 7


# ------------------------------------------- der eigentliche Zweck des Umbaus


def test_bestand_ueberlebt_den_ortswechsel_ohne_reparatur(tmp_path, monkeypatch):
    """Der 0.3.1-Fehlerfall, diesmal von vornherein verhindert.

    Sicherung an einem anderen Ort eingespielt = der ganze Datenbestand
    liegt woanders. Mit absolutem `archive_path` zeigte danach jede Zeile ins
    Leere; relativ gespeichert findet sie ihre Datei ohne jede Reparatur.
    """
    alt = tmp_path / "alt"
    home = richte_ein(alt)
    monkeypatch.setenv("BUEROKRATOR_HOME", str(alt))
    init_database()

    datei = lege_ab(home / "archive", "2024", "Rechnungen", "rechnung.pdf")

    document_id = insert_document(
        filename=datei.name,
        archive_path=str(datei),
        document_type="invoice",
        extracted_data={"issuer": "Musterfirma GmbH"},
    )

    gespeichert = roher_pfad(home / "database" / "buerokrator.db", document_id)

    # Umzug: dieselbe Struktur, anderer Ort.
    neu = tmp_path / "neu"
    shutil.copytree(alt, neu)
    monkeypatch.setenv("BUEROKRATOR_HOME", str(neu))

    aufgeloest = resolve_archive_path(gespeichert)

    assert aufgeloest.exists()
    assert aufgeloest == neu / "profiles" / "1" / "archive" / "2024" / "Rechnungen" / "rechnung.pdf"

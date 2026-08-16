"""Dashboard: alle elf Kategorien als Kacheln, dazu die Archivgröße.

Bisher zeigte das Dashboard vier von elf Typen — die Auswahl war historisch
gewachsen, nicht begründet, und ausgerechnet die größte Gruppe fehlte.
`counts_by_type` liefert längst alle.

Elf Zahlen, die nirgendwohin führen, wären Dekoration statt Bedienung:
deshalb ist jede Kachel ein Weg in die gefilterte Liste. Die Null ist der
Sonderfall — sie führt nirgendwohin und darf nicht so aussehen, als täte sie
es.

⚠️ Die Archivgröße ist eine Bestandszahl. Geprüft wird deshalb gegen ein
**erfundenes** Archiv, nie gegen das echte.
"""

import pytest
from nicegui.testing import User

import src.database.database as database
from src.core.document_types import DOCUMENT_TYPE_LABELS, DOCUMENT_TYPES
from src.core.size_utils import format_bytes

pytest_plugins = ["nicegui.testing.user_plugin"]


CONFIG = "\n".join(
    [
        "paths:",
        "  inbox: ./inbox",
        "  archive: ./archive",
        "  exports: ./exports",
        "database:",
        "  path: ./database/buerokrator.db",
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


def _dokumente(**je_typ):
    """Legt Dokumente je Dokumenttyp an — erfundene Werte, feste Anzahl."""
    from src.database.database import get_connection

    conn = get_connection()

    for document_type, anzahl in je_typ.items():
        for lauf in range(anzahl):
            conn.execute(
                "INSERT INTO documents (filename, document_type, verified)"
                " VALUES (?, ?, 1)",
                (f"muster-{document_type}-{lauf}.pdf", document_type),
            )

    conn.commit()
    conn.close()


def _archiv(dateien):
    """Erfundenes Archiv: {relativer Pfad: Byteanzahl}.

    Ins App-Home, nicht neben die Config: die Pfade der Config stehen relativ
    und werden gegen das PROFIL aufgelöst (ADR 015).
    """
    from src.core.app_home import get_app_home

    for pfad, groesse in dateien.items():
        ziel = get_app_home() / "archive" / pfad
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(b"x" * groesse)


# ------------------------------------------------------- Groessenformat


def test_format_bytes_waechst_ueber_alle_einheiten():
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(2048) == "2 KB"
    assert format_bytes(5 * 1024 * 1024) == "5,0 MB"
    assert format_bytes(3 * 1024**3) == "3,0 GB"


def test_format_bytes_schreibt_deutsch():
    """Die Oberfläche ist durchweg deutsch — ein Punkt als Dezimaltrenner
    stünde zwischen lauter Kommazahlen (vgl. layout.format_euro)."""
    assert "," in format_bytes(int(1.5 * 1024 * 1024))
    assert "." not in format_bytes(int(1.5 * 1024 * 1024))


def test_format_bytes_vertraegt_leere_werte():
    assert format_bytes(None) == "-"


# --------------------------------------------------------- Archivgroesse


def test_archivgroesse_summiert_nur_das_archiv(isolierte_instanz):
    """Datenbank, Sicherungen und Papierkorb gehören nicht dazu — sie sind
    keine abgelegten Dokumente und würden die Zahl unerklärlich machen."""
    from src.core.app_home import get_app_home
    from src.services.stats_service import get_archive_size

    _archiv({"2024/Rechnungen/a.pdf": 1000, "2023/Wohnen/b.pdf": 500})

    papierkorb = get_app_home() / "trash"
    papierkorb.mkdir(parents=True, exist_ok=True)
    (papierkorb / "geloescht.pdf").write_bytes(b"x" * 9999)

    assert get_archive_size() == 1500


def test_archivgroesse_ohne_archiv_ist_null(isolierte_instanz):
    from src.services.stats_service import get_archive_size

    assert get_archive_size() == 0


def test_dashboard_daten_tragen_die_archivgroesse(isolierte_instanz):
    from src.services.stats_service import get_dashboard_data

    _archiv({"2024/Rechnungen/a.pdf": 2048})

    assert get_dashboard_data()["archive_size"] == 2048


# --------------------------------------------------------- die Kacheln


@pytest.mark.asyncio
async def test_dashboard_zeigt_alle_elf_kategorien(user: User):
    """Die alte Auswahl war historisch: vier von elf, ohne die größte Gruppe."""
    _dokumente(invoice=3, employment=2)

    await user.open("/")

    for document_type in DOCUMENT_TYPES:
        await user.should_see(marker=f"kachel-{document_type}")


@pytest.mark.asyncio
async def test_dashboard_nennt_gesamtzahl_und_archivgroesse(
    user: User, isolierte_instanz
):
    _dokumente(invoice=2)
    _archiv({"2024/Rechnungen/a.pdf": 4096})

    await user.open("/")

    # Ganze Zeile, nicht nur "2 Dokumente": seit die Kacheln ihre Anzahl
    # ebenso schreiben, träfe der kurze Text auch die Rechnungs-Kachel und
    # der Test wäre grün, ohne den Untertitel je gesehen zu haben.
    await user.should_see("2 Dokumente archiviert · 4 KB im Archiv")


@pytest.mark.asyncio
async def test_kachel_nennt_kategorie_und_anzahl(user: User):
    """Oben der Name, darunter die Anzahl in Worten statt als nackte Zahl."""
    _dokumente(invoice=3)

    await user.open("/")

    await user.should_see("Rechnung")
    await user.should_see("3 Dokumente")


@pytest.mark.asyncio
async def test_kachel_schreibt_die_einzahl_richtig(user: User):
    """„1 Dokumente" läse sich wie ein Fehler in der Anwendung."""
    _dokumente(invoice=1)

    await user.open("/")

    await user.should_see("1 Dokument")


@pytest.mark.asyncio
async def test_leere_kachel_nennt_null_dokumente(user: User):
    _dokumente(invoice=1)

    await user.open("/")

    await user.should_see("0 Dokumente")


@pytest.mark.asyncio
async def test_kachel_fuehrt_in_die_gefilterte_liste(user: User):
    _dokumente(invoice=2, employment=3)

    await user.open("/")
    user.find(marker="kachel-employment").click()

    await user.should_see("3 Dokumente gefunden")


@pytest.mark.asyncio
async def test_leere_kachel_fuehrt_nirgendwohin(user: User):
    """Eine 0 ist kein Weg. Klickbar sähe sie aus wie einer."""
    _dokumente(invoice=1)

    await user.open("/")
    user.find(marker="kachel-health").click()

    # Immer noch das Dashboard — kein Wechsel in eine leere Liste.
    await user.should_see("Aufgaben")


# ------------------------------------------- Filter ueber den Query-Parameter


@pytest.mark.asyncio
async def test_liste_nimmt_den_typ_aus_der_adresse(user: User):
    _dokumente(invoice=2, employment=3)

    await user.open("/dokumente?typ=employment")

    await user.should_see("3 Dokumente gefunden")
    await user.should_see(DOCUMENT_TYPE_LABELS["employment"])


@pytest.mark.asyncio
async def test_unbekannter_typ_zeigt_alles_statt_nichts(user: User):
    """Ein unbekannter Wert darf nicht in eine leere Liste führen — das sähe
    aus wie ein leerer Bestand."""
    _dokumente(invoice=2, employment=3)

    await user.open("/dokumente?typ=quatsch")

    await user.should_see("5 Dokumente gefunden")


@pytest.mark.asyncio
async def test_kachel_setzt_alte_filter_zurueck(user: User):
    """Die Kachel verspricht ALLE Dokumente ihrer Kategorie.

    Bliebe ein alter Suchbegriff stehen, zeigte sie weniger — und niemand
    sähe, warum.
    """
    _dokumente(invoice=2, employment=3)

    await user.open("/dokumente?typ=invoice")
    await user.should_see("2 Dokumente gefunden")

    await user.open("/dokumente?typ=employment")
    await user.should_see("3 Dokumente gefunden")

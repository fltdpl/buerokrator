"""Smoke-Tests für das NiceGUI-Frontend (User-Fixture, ohne Browser).

Läuft gegen eine leere Test-Datenbank (tmp_path): prüft, dass alle Seiten
fehlerfrei bauen und die Kern-Navigation funktioniert.
"""

import os
from pathlib import Path

import pytest

from nicegui import ui
from nicegui.testing import User

pytest_plugins = ["nicegui.testing.user_plugin"]


@pytest.fixture(autouse=True)
def isolated_project(tmp_path, monkeypatch):
    """Leere Config + DB, damit die Tests nie die echte Datenbank berühren."""
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
                "    tax: Steuern",
                "    insurance: Versicherungen",
                "    pension: Vorsorge",
                "    bank: Bank",
                "    housing: Wohnen",
                "    employment: Arbeit",
                "    legal: Recht",
                "    unknown: Sonstiges",
            ]
        ),
        encoding="utf-8",
    )
    # NiceGUI beobachtet sein Storage-Verzeichnis; ohne das Verzeichnis
    # schlägt der Watchdog beim App-Start fehl.
    (tmp_path / ".nicegui").mkdir()
    monkeypatch.chdir(tmp_path)

    from src.database.init_database import init_database

    init_database()


@pytest.mark.asyncio
async def test_dashboard_renders(user: User):
    await user.open("/")
    await user.should_see("Dashboard")
    await user.should_see("Dokumente archiviert")
    # Beenden-Eintrag der Seitenleiste (auf jeder Seite erreichbar)
    await user.should_see("Beenden")


@pytest.mark.asyncio
async def test_documents_list_renders_empty(user: User):
    await user.open("/dokumente")
    await user.should_see("Keine Dokumente gefunden.")


@pytest.mark.asyncio
async def test_document_detail_renders(user: User):
    from src.database.document_repository import insert_document

    document_id = insert_document(
        "2024-01-01_Musterversand_42EUR.pdf",
        "archive/2024/Rechnungen/2024-01-01_Musterversand_42EUR.pdf",
        "invoice",
        {"issuer": "Musterversand", "amount": 42.0, "document_date": "01.01.2024"},
    )

    await user.open(f"/dokumente/{document_id}")
    await user.should_see("Speichern & Freigeben")
    await user.should_see("Aussteller")
    # Dokument-ID im Kopf sichtbar.
    await user.should_see(f"ID {document_id}")


@pytest.mark.asyncio
async def test_employment_detail_shows_subject_and_tax_relevant(user: User):
    from src.database.document_repository import insert_document

    document_id = insert_document(
        "2024-03-01_ACME_Kuendigung.pdf",
        "archive/2024/Arbeit/2024-03-01_ACME_Kuendigung.pdf",
        "employment",
        {
            "document_subtype": "kuendigung",
            "issuer": "ACME AG",
            "document_date": "01.03.2024",
            "subject": "Ordentliche Kündigung",
        },
    )

    await user.open(f"/dokumente/{document_id}")
    await user.should_see("Arbeit")
    await user.should_see("Betreff")
    await user.should_see("Steuerrelevant")


@pytest.mark.asyncio
async def test_document_detail_unknown_id(user: User):
    await user.open("/dokumente/99999")
    await user.should_see("Dokument nicht gefunden.")


@pytest.mark.asyncio
async def test_import_page_renders(user: User):
    await user.open("/import")
    await user.should_see("Stapel-Import")
    await user.should_see("Keine Dateien im Inbox-Ordner.")


@pytest.mark.asyncio
async def test_analyse_page_renders_empty(user: User):
    await user.open("/analyse")
    # Tab Steuer (vorgewählt) und Tab Einkommen, beide mit Leer-Hinweis.
    await user.should_see("Noch keine archivierten Dokumente vorhanden.")
    await user.should_see("Noch keine geprüften Lohnsteuerbescheinigungen")


@pytest.mark.asyncio
async def test_steuer_route_redirects_to_analyse(user: User):
    await user.open("/steuer")
    await user.should_see("Analyse")


@pytest.mark.asyncio
async def test_settings_page_renders(user: User):
    await user.open("/einstellungen")
    await user.should_see("Einstellungen")
    await user.should_see("Gefahrenzone")
    await user.should_see("Beenden")
    # Aliase-Tab: Editor über der (bei Bedarf angelegten) Vorlagendatei.
    await user.should_see("Aussteller-Aliase")


@pytest.mark.asyncio
async def test_trash_page_renders_empty(user: User):
    await user.open("/papierkorb")
    await user.should_see("Der Papierkorb ist leer.")


@pytest.mark.asyncio
async def test_trash_page_lists_deleted_files(user: User, tmp_path):
    trash = tmp_path / "trash"
    trash.mkdir()
    (trash / "geloescht.pdf").write_text("x", encoding="utf-8")

    await user.open("/papierkorb")
    await user.should_see("geloescht.pdf")
    await user.should_see("Wiederherstellen")


@pytest.mark.asyncio
async def test_setup_page_renders(user: User):
    await user.open("/einrichtung")
    await user.should_see("Einrichtung")
    await user.should_see("Erneut prüfen")


@pytest.mark.asyncio
async def test_dashboard_redirects_fresh_instance_to_setup(user: User, tmp_path):
    # Frische Instanz nachstellen: DB weg, kein Abschluss-Marker.
    (tmp_path / "database" / "buerokrator.db").unlink()

    await user.open("/")
    await user.should_see("einsatzbereit")


@pytest.mark.asyncio
async def test_detail_marks_empty_required_field(user: User):
    from src.database.document_repository import insert_document

    # Ohne Aussteller: das Feld ist Pflicht und muss beim Prüfen auffallen.
    document_id = insert_document(
        "2024-01-01_unbekannt.pdf",
        "archive/2024/Rechnungen/2024-01-01_unbekannt.pdf",
        "invoice",
        {"amount": 42.0, "document_date": "01.01.2024"},
    )

    await user.open(f"/dokumente/{document_id}")
    await user.should_see("Pflichtfeld(er) leer")


@pytest.mark.asyncio
async def test_analyse_page_renders_anlagen_and_income_view(user: User, monkeypatch):
    # Mit Bestand: Anlagen-Ansicht (Tab Steuer) und Einkommens-Auswertung
    # (Tab Einkommen) bauen beide. Zahlen erfunden.
    import src.database.database as database
    from src.database.document_repository import insert_document
    from src.database.set_document_verified import set_document_verified

    # Schema-Migration im frischen tmp_path erneut ausführen (das Flag ist
    # prozess-global und durch vorherige Tests schon gesetzt).
    monkeypatch.setattr(database, "_schema_ready", False)

    document_id = insert_document(
        filename="lstb.pdf",
        archive_path="archive/2025/Arbeit/lstb.pdf",
        document_type="employment",
        extracted_data={
            "document_subtype": "lohnsteuerbescheinigung",
            "employer": "Musterfirma GmbH",
            "tax_year": "2025",
            "gross_amount": 38500.0,
        },
    )
    set_document_verified(document_id, 1)

    await user.open("/analyse")
    await user.should_see("Anlage N")
    await user.should_see("Anlage Vorsorgeaufwand")
    await user.should_see("Anlage KAP")
    await user.should_see("Bruttoarbeitslohn (LStB Zeile 3)")
    # Einkommen-Tab: Jahreszeile mit Summen aus der geprüften LStB.
    await user.should_see("Jahreseinkommen")
    await user.should_see("Werte je Jahr")


# Bewusst der LETZTE Test der Datei: der direkte Import von src.frontend.main
# verstellt die App-Registrierung — User-Fixture-Tests danach laufen ins 404.
def test_nicegui_storage_path_points_to_app_home(tmp_path):
    """NiceGUI-Storage darf nicht cwd-relativ liegen (Packaging).

    src.frontend.main setzt NICEGUI_STORAGE_PATH beim Import auf das
    App-Home. Geprüft wird in einem SUBPROZESS: ein Import im Testprozess
    legt das Modul in sys.modules ab, sodass die @ui.page-Dekoratoren beim
    Neuaufbau der App für nachfolgende Tests nicht mehr laufen — jede
    weitere Seite antwortete dann mit 404.
    """
    import subprocess
    import sys

    # main.py setzt die Variable per setdefault — eine geerbte Belegung
    # aus dem Testprozess würde gewinnen und den Test wertlos machen.
    child_env = {
        key: value
        for key, value in os.environ.items()
        if key != "NICEGUI_STORAGE_PATH"
    }
    child_env["BUEROKRATOR_HOME"] = str(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; import src.frontend.main; "
            "print(os.environ['NICEGUI_STORAGE_PATH'])",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=child_env,
    )

    assert result.returncode == 0, result.stderr

    storage_path = Path(result.stdout.strip())

    assert storage_path.is_absolute()
    assert storage_path.name == ".nicegui"
    assert storage_path.parent == tmp_path


@pytest.mark.asyncio
async def test_import_seite_nennt_die_fehlerursache(user: User):
    """Ein Fehlschlag darf nicht nur als Dateiname erscheinen (Review).

    Vorher schluckte process() jede Exception zu None; die Import-Seite
    zeigte den Namen und nichts sonst — die Ursache stand ausschließlich
    in der Logdatei.
    """
    from src.services import import_job

    import_job.finish(
        succeeded=[],
        duplicates=[],
        failed=[
            {
                "source_name": "kaputt.pdf",
                "error": "TesseractNotFoundError: tesseract nicht gefunden",
            }
        ],
    )

    try:
        await user.open("/import")
        await user.should_see("1 Dokument(e) fehlgeschlagen")
        await user.should_see("tesseract nicht gefunden")
        await user.should_see("liegen unverändert im Inbox-Ordner")

    finally:
        import_job._reset_for_tests()


@pytest.mark.asyncio
async def test_dokumentenliste_baut_mit_bestand_und_bulk_leiste(user: User):
    """Die leere Liste allein deckt den Seitenaufbau nicht ab.

    Ohne Zeilen wird der Tabellen- und Bulk-Aktions-Zweig nie ausgeführt —
    ein Fehler dort (z. B. ein nicht mehr existierender Aufruf) blieb
    unbemerkt grün.
    """
    from src.database.document_repository import insert_document

    insert_document(
        "2024-01-01_Musterversand_42EUR.pdf",
        "archive/2024/Rechnungen/2024-01-01_Musterversand_42EUR.pdf",
        "invoice",
        {"issuer": "Musterversand", "amount": 42.0, "document_date": "01.01.2024"},
    )

    await user.open("/dokumente")
    # Der Tabellenzweig lief (die leere Liste bricht vorher ab) …
    await user.should_see("1 Dokumente gefunden")
    await user.should_not_see("Keine Dokumente gefunden.")
    # Die Bulk-Leiste ist bei leerer Auswahl unsichtbar und damit nicht
    # prüfbar — dass sie fehlerfrei GEBAUT wurde, zeigt das vollständige
    # Rendern der Seite bis zum Fuß.
    await user.should_see("CSV Export")


@pytest.mark.asyncio
async def test_detail_warnt_vor_inhaltlicher_dublette(user: User):
    """Zwei Scans desselben Belegs: der Prüf-Workflow zeigt den Hinweis.

    Der Inhalts-Hash greift hier nicht (verschiedene Dateien), die Warnung
    kommt aus dem Vergleich der erkannten Werte.
    """
    from src.database.document_repository import insert_document

    beleg = {
        "issuer": "Musterversand",
        "amount": 42.0,
        "document_date": "01.01.2024",
    }
    insert_document(
        "2024-01-01_Musterversand_42EUR.pdf",
        "archive/2024/Rechnungen/2024-01-01_Musterversand_42EUR.pdf",
        "invoice",
        dict(beleg),
    )
    zweiter = insert_document(
        "2024-01-01_Musterversand_42EUR_scan.pdf",
        "archive/2024/Rechnungen/2024-01-01_Musterversand_42EUR_scan.pdf",
        "invoice",
        dict(beleg),
    )

    await user.open(f"/dokumente/{zweiter}")
    await user.should_see("Mögliche Dublette")
    await user.should_see("2024-01-01_Musterversand_42EUR.pdf")


@pytest.mark.asyncio
async def test_dublettenhinweis_nennt_das_abweichende_feld(user: User):
    """Was widerspricht, steht neben dem Treffergrund.

    Aussteller, Betrag und Datum stimmen, die Rechnungsnummern nicht — genau
    daran entscheidet sich am Original, ob es derselbe Beleg ist.
    """
    from src.database.document_repository import insert_document

    beleg = {
        "issuer": "Musterversand",
        "amount": 42.0,
        "document_date": "01.01.2024",
    }
    insert_document(
        "a.pdf",
        "archive/2024/Rechnungen/a.pdf",
        "invoice",
        dict(beleg, invoice_number="RE-1001"),
    )
    zweiter = insert_document(
        "b.pdf",
        "archive/2024/Rechnungen/b.pdf",
        "invoice",
        dict(beleg, invoice_number="RE-1002"),
    )

    await user.open(f"/dokumente/{zweiter}")
    await user.should_see("Mögliche Dublette")
    await user.should_see("abweichend: Rechnungsnummer")


@pytest.mark.asyncio
async def test_aussteller_gedaechtnis_meldet_abweichenden_typ(user: User):
    """Der Aussteller lieferte bisher ausnahmslos Vorsorge — jetzt Versicherung.

    Der Hinweis meldet das, ändert aber nichts: der erkannte Typ bleibt stehen.
    """
    from src.database.document_repository import insert_document
    from src.database.set_document_verified import set_document_verified

    for name in ("a.pdf", "b.pdf"):
        vorher = insert_document(
            name,
            f"archive/2024/Vorsorge/{name}",
            "pension",
            {"issuer": "Musterkasse"},
        )
        set_document_verified(vorher, 1)

    abweichend = insert_document(
        "c.pdf",
        "archive/2024/Versicherungen/c.pdf",
        "insurance",
        {"issuer": "Musterkasse"},
    )

    await user.open(f"/dokumente/{abweichend}")
    await user.should_see("ausnahmslos als Vorsorge")
    await user.should_see("erkannt als Versicherung")


@pytest.mark.asyncio
async def test_gemischter_aussteller_zeigt_keinen_gedaechtnis_hinweis(user: User):
    """Anbieter mit mehreren Sparten dürfen den Prüf-Workflow nicht zumüllen."""
    from src.database.document_repository import insert_document
    from src.database.set_document_verified import set_document_verified

    for name, typ in (("a.pdf", "pension"), ("b.pdf", "insurance")):
        vorher = insert_document(
            name, f"archive/2024/x/{name}", typ, {"issuer": "Musterkasse"}
        )
        set_document_verified(vorher, 1)

    weiteres = insert_document(
        "c.pdf", "archive/2024/x/c.pdf", "insurance", {"issuer": "Musterkasse"}
    )

    await user.open(f"/dokumente/{weiteres}")
    await user.should_see("Speichern & Freigeben")
    await user.should_not_see("ausnahmslos als")


@pytest.mark.asyncio
async def test_detail_ohne_dublette_zeigt_keinen_hinweis(user: User):
    from src.database.document_repository import insert_document

    document_id = insert_document(
        "2024-01-01_Musterversand_42EUR.pdf",
        "archive/2024/Rechnungen/2024-01-01_Musterversand_42EUR.pdf",
        "invoice",
        {"issuer": "Musterversand", "amount": 42.0, "document_date": "01.01.2024"},
    )

    await user.open(f"/dokumente/{document_id}")
    await user.should_see("Speichern & Freigeben")
    await user.should_not_see("Mögliche Dublette")


@pytest.mark.asyncio
async def test_suche_zeigt_die_fundstelle_im_volltext(user: User, monkeypatch):
    """Die Liste sagt, WARUM ein Dokument gefunden wurde.

    Ohne die Passage bleibt bei einem Volltext-Treffer offen, an welcher
    Stelle der Begriff steht — die Zeile selbst zeigt ihn nicht.

    Der Suchbegriff geht direkt in den Filterzustand: das Eingabefeld hat
    ein debounce von 400 ms, das im Test nicht auslöst.
    """
    from src.database.document_repository import insert_document
    from src.frontend.pages import documents

    insert_document(
        "2024-01-01_Musterversand.pdf",
        "archive/2024/Rechnungen/2024-01-01_Musterversand.pdf",
        "invoice",
        {"issuer": "Musterversand", "amount": 42.0, "document_date": "01.01.2024"},
        document_text=(
            "Musterversand GmbH, Beispielstadt. Position: Wartung "
            "Heizungsanlage, Arbeitslohn 210,00 EUR."
        ),
    )

    monkeypatch.setitem(documents._FILTER_STATE, "search", "Heizungsanlage")

    await user.open("/dokumente")
    await user.should_see("1 Dokumente gefunden")

    # Der Spaltenkopf ist Teil der Tabellenkonfiguration und für den
    # Simulator kein eigenes Element — geprüft wird deshalb die Tabelle.
    table = list(user.find(ui.table).elements)[0]

    assert any(spalte["name"] == "text_snippet" for spalte in table.columns)
    assert "<mark>Heizungsanlage</mark>" in table.rows[0]["text_snippet"]

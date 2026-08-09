"""Tags, Schritt 1: Schema, Dienst, Vergabe in der Detailansicht.

Tags sind **flach**: ein Wert, keine Systematik. Ein Namensraum
(`koerper:knie`) war der erste Entwurf und wurde verworfen — er löst ein
Problem, das erst bei Hunderten von Tags entsteht, verlangt aber schon vor
dem ERSTEN Tag eine Ordnung. Gruppieren kann man später immer noch.

Tags sind für kein Dokument Pflicht: ohne vergebene Tags zeigt die
Detailansicht nur einen kleinen Knopf.

Der teuerste Fehler eines Tag-Systems ist die Dublette („Knie", "knie",
"knie "). Die Normalisierung ist deshalb der am dichtesten getestete Teil —
und sie behält die Schreibweise für die Anzeige, denn deutsche Substantive
kleinzuschreiben sähe falsch aus.
"""

import pytest
from nicegui.testing import User

from src.core.app_home import reset_profile_cache
from src.database.database import open_connection
from src.database.delete_document import delete_document
from src.database.document_repository import insert_document
from src.database.init_database import init_database
from src.services import import_job
from src.services.tag_service import (
    add_to_selection,
    list_tags,
    normalize_tag_name,
    remove_from_selection,
    set_document_tags,
    tag_key,
    tags_for_document,
)

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
        "    health: Gesundheit",
        "    unknown: Sonstiges",
    ]
)


@pytest.fixture(autouse=True)
def isolierte_installation(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(CONFIG, encoding="utf-8")
    (tmp_path / ".nicegui").mkdir()
    monkeypatch.chdir(tmp_path)

    reset_profile_cache()
    import_job._reset_for_tests()

    init_database()

    yield

    reset_profile_cache()
    import_job._reset_for_tests()


def _dokument(dateiname="a.pdf", typ="health"):
    return insert_document(dateiname, f"archive/2026/Gesundheit/{dateiname}", typ, {})


# --- Normalisierung: Dublettenabwehr ohne Schreibweise zu verlieren ----


@pytest.mark.parametrize(
    "eingabe, erwartet",
    [
        ("Knie-OP", "Knie-OP"),
        ("  Auto  ", "Auto"),
        ("Steuer   2025", "Steuer 2025"),
        ("wichtig", "wichtig"),
        ("Ärztliche Unterlagen", "Ärztliche Unterlagen"),
    ],
)
def test_anzeigename_bleibt_erhalten(eingabe, erwartet):
    assert normalize_tag_name(eingabe) == erwartet


@pytest.mark.parametrize("eingabe", ["", "   ", "\t\n", "---", "a" * 61])
def test_unbrauchbare_eingabe_wird_abgewiesen(eingabe):
    with pytest.raises(ValueError):
        normalize_tag_name(eingabe)


def test_doppelpunkt_ist_erlaubt_denn_es_gibt_keine_namensraeume_mehr():
    assert normalize_tag_name("Az: 4711") == "Az: 4711"


@pytest.mark.parametrize(
    "eins, zwei",
    [
        ("Knie", "knie"),
        ("Knie-OP", "KNIE-OP"),
        ("Straße", "STRASSE"),
        ("Ärzte", "ärzte"),
    ],
)
def test_schluessel_faellt_bei_gleicher_bedeutung_zusammen(eins, zwei):
    assert tag_key(eins) == tag_key(zwei)


def test_schluessel_trennt_verschiedene_woerter():
    assert tag_key("Knie") != tag_key("Knies")


# --- Auswahl in der Detailansicht (framework-frei) ---------------------


def test_hinzufuegen_haengt_an_und_normalisiert():
    assert add_to_selection([], "  Knie-OP ") == ["Knie-OP"]
    assert add_to_selection(["Knie-OP"], "Auto") == ["Knie-OP", "Auto"]


def test_hinzufuegen_erkennt_die_dublette_trotz_anderer_schreibweise():
    with pytest.raises(ValueError):
        add_to_selection(["Knie-OP"], "knie-op")


def test_hinzufuegen_veraendert_die_uebergebene_liste_nicht():
    auswahl = ["Auto"]

    add_to_selection(auswahl, "Knie")

    assert auswahl == ["Auto"]


def test_entfernen_ignoriert_die_schreibweise():
    assert remove_from_selection(["Knie-OP", "Auto"], "knie-op") == ["Auto"]
    assert remove_from_selection(["Auto"], "gibt-es-nicht") == ["Auto"]


# --- Schema ------------------------------------------------------------


def test_tabellen_und_spalten():
    with open_connection() as conn:
        namen = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"tags", "document_tags"} <= namen

        spalten = {row["name"] for row in conn.execute("PRAGMA table_info(tags)")}
        assert {"id", "name", "key", "color_index"} <= spalten
        # Der Namensraum ist weg.
        assert "namespace" not in spalten


def test_alte_tag_tabelle_wird_ersetzt_statt_stehenzubleiben():
    """Der verworfene erste Entwurf (mit namespace) liegt auf dieser Maschine
    schon in einer Datenbank. CREATE TABLE IF NOT EXISTS würde sie stumm
    stehen lassen, und jede Abfrage liefe gegen fehlende Spalten."""
    with open_connection() as conn:
        conn.execute("DROP TABLE document_tags")
        conn.execute("DROP TABLE tags")
        conn.execute(
            """
            CREATE TABLE tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE document_tags (
                document_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL
            )
            """
        )
        conn.commit()

    init_database()

    with open_connection() as conn:
        spalten = {row["name"] for row in conn.execute("PRAGMA table_info(tags)")}

    assert "namespace" not in spalten
    assert "key" in spalten


def test_name_ist_unabhaengig_von_der_schreibweise_eindeutig():
    erstes = _dokument("a.pdf")
    zweites = _dokument("b.pdf")

    set_document_tags(erstes, ["Knie-OP"])
    set_document_tags(zweites, ["knie-op"])

    assert len(list_tags()) == 1


# --- Zuordnung ---------------------------------------------------------


def test_tags_setzen_lesen_und_ersetzen():
    doc = _dokument()

    set_document_tags(doc, ["Knie-OP", "MRT"])

    assert [tag["name"] for tag in tags_for_document(doc)] == ["Knie-OP", "MRT"]

    set_document_tags(doc, ["Knie-OP", "Reha"])

    assert [tag["name"] for tag in tags_for_document(doc)] == ["Knie-OP", "Reha"]


def test_leere_liste_entfernt_alle_zuordnungen():
    doc = _dokument()
    set_document_tags(doc, ["Auto"])

    set_document_tags(doc, [])

    assert tags_for_document(doc) == []


def test_doppelte_eingabe_im_selben_aufruf_zaehlt_einmal():
    doc = _dokument()

    set_document_tags(doc, ["Auto", "auto", "AUTO"])

    assert len(tags_for_document(doc)) == 1


def test_die_erste_schreibweise_gewinnt():
    """Wer „Knie-OP" angelegt hat, soll es nicht durch ein späteres
    „knie-op" an einem anderen Dokument umbenannt bekommen."""
    erstes = _dokument("a.pdf")
    zweites = _dokument("b.pdf")

    set_document_tags(erstes, ["Knie-OP"])
    set_document_tags(zweites, ["knie-op"])

    assert [tag["name"] for tag in tags_for_document(zweites)] == ["Knie-OP"]


def test_liste_kennt_die_nutzung_und_zeigt_auch_verwaiste():
    erstes = _dokument("a.pdf")
    zweites = _dokument("b.pdf")
    set_document_tags(erstes, ["Auto", "Knie-OP"])
    set_document_tags(zweites, ["Auto"])
    set_document_tags(erstes, ["Auto"])

    nutzung = {tag["name"]: tag["usage"] for tag in list_tags()}

    assert nutzung == {"Auto": 2, "Knie-OP": 0}


def test_geloeschtes_dokument_laesst_keine_verwaisten_zuordnungen():
    """SQLite erzwingt Fremdschluessel nur mit PRAGMA foreign_keys=ON — das
    ist hier NICHT gesetzt, ON DELETE CASCADE liefe also ins Leere."""
    doc = _dokument()
    set_document_tags(doc, ["Auto"])

    delete_document(doc)

    with open_connection() as conn:
        offen = conn.execute(
            "SELECT COUNT(*) AS n FROM document_tags WHERE document_id = ?",
            (doc,),
        ).fetchone()["n"]

    assert offen == 0
    assert [tag["name"] for tag in list_tags()] == ["Auto"]


def test_farben_werden_reihum_vergeben():
    """Damit zwei benachbarte Tags nicht denselben Punkt tragen."""
    doc = _dokument()

    set_document_tags(doc, ["Auto", "Knie-OP", "Steuer"])

    farben = [tag["color_index"] for tag in tags_for_document(doc)]

    assert len(set(farben)) == 3


def test_tags_beruehren_die_extrahierten_felder_nicht():
    from src.core.document_fields import ALLOWED_FIELDS

    for felder in ALLOWED_FIELDS.values():
        assert "tags" not in felder


# --- Oberflaeche -------------------------------------------------------


@pytest.mark.asyncio
async def test_ohne_tags_bleibt_die_seite_ruhig(user: User):
    """Tags sind kein Pflichtfeld: ohne vergebene Tags steht da nur ein
    kleiner Knopf, keine Ueberschrift und keine leere Struktur."""
    doc = _dokument()

    await user.open(f"/dokumente/{doc}")

    await user.should_see(marker="tag-plus")
    await user.should_not_see("Namensraum")
    await user.should_not_see("Namensräume")


@pytest.mark.asyncio
async def test_vergebene_tags_erscheinen_als_chips(user: User):
    doc = _dokument()
    set_document_tags(doc, ["Knie-OP", "MRT"])

    await user.open(f"/dokumente/{doc}")

    await user.should_see("Knie-OP")
    await user.should_see("MRT")


@pytest.mark.asyncio
async def test_neues_tag_wird_erst_beim_speichern_geschrieben(user: User):
    """Anlegen darf kein Nebeneffekt sein: wer die Seite verlaesst, ohne zu
    speichern, soll kein Vokabular hinterlassen haben."""
    doc = _dokument()

    await user.open(f"/dokumente/{doc}")
    user.find(marker="tag-eingabe").type("Knie-OP")
    user.find(marker="tag-neu").click()

    await user.should_see("Knie-OP")
    assert list_tags() == []

    user.find(marker="speichern").click()
    await user.should_see("Dokumente")

    assert [tag["name"] for tag in tags_for_document(doc)] == ["Knie-OP"]


@pytest.mark.asyncio
async def test_vorhandenes_tag_laesst_sich_ankreuzen(user: User):
    """Der haeufige Fall ist nicht Anlegen, sondern Wiederverwenden."""
    anderes = _dokument("b.pdf")
    set_document_tags(anderes, ["Auto"])

    doc = _dokument("a.pdf")

    await user.open(f"/dokumente/{doc}")
    user.find(marker="tag-auswahl-Auto").click()
    user.find(marker="speichern").click()
    await user.should_see("Dokumente")

    assert [tag["name"] for tag in tags_for_document(doc)] == ["Auto"]

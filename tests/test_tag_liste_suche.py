"""Tags, Schritt 3: in der Trefferliste sichtbar und im Volltext auffindbar.

Die Volltextsuche ist eine External-Content-FTS5-Tabelle über `documents`;
Tags liegen aber in eigenen Tabellen und wären damit unsichtbar für sie.
Deshalb trägt `documents` eine abgeleitete Spalte `tags_text`, die bei jeder
Tag-Änderung mitgeschrieben wird — die vorhandenen Trigger auf `documents`
halten den Index dann von selbst aktuell.

Der teure Teil daran ist nicht die Spalte, sondern die Spaltenliste: sie
bestimmt die bm25-Gewichte und den Spaltenindex der Fundstelle. Beides ist
hier gepinnt, weil ein Verrutschen still falsche Ergebnisse liefert.
"""



import pytest

from src.core.app_home import reset_profile_cache
from src.database.database import open_connection
from src.database.document_repository import insert_document
from src.database.init_database import FTS_COLUMNS, SCHEMA_VERSION, init_database
from src.database.search import _BM25_WEIGHTS, _SNIPPET_COLUMN, search_documents
from src.services import import_job
from src.services.document_service import build_table_rows
from src.database.list_documents import list_documents
from src.services.tag_service import (
    add_tag_to_documents,
    remove_tag_from_documents,
    set_document_tags,
)

CONFIG = "\n".join(
    [
        "paths:",
        "  inbox: ./inbox",
        "  archive: ./archive",
        "  exports: ./exports",
        "database:",
        "  path: ./database/buerokrator.db",
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
    monkeypatch.chdir(tmp_path)

    reset_profile_cache()
    import_job._reset_for_tests()

    init_database()

    yield

    reset_profile_cache()
    import_job._reset_for_tests()


def _dokument(dateiname="a.pdf", typ="health", text="Erfundener Text."):
    return insert_document(
        dateiname,
        f"archive/2026/Gesundheit/{dateiname}",
        typ,
        {"issuer": "Musterpraxis", "document_date": "12.03.2026"},
        document_text=text,
    )


def _tags_text(document_id):
    with open_connection() as conn:
        return conn.execute(
            "SELECT tags_text FROM documents WHERE id = ?", (document_id,)
        ).fetchone()["tags_text"]


# --- Spaltenliste: gepinnt, weil ein Verrutschen still schadet ---------


def test_schemaversion_wurde_erhoeht():
    """Die Tag-Erweiterung brauchte v6 — spätere Stände sind erlaubt.

    Ein exakter Wert stand hier zuerst; er hielt aber nicht den Zweck fest
    (dass die FTS-Erweiterung den Stand hebt), sondern nur den Tagesstand und
    fiel bei der nächsten, völlig unbeteiligten Migration.
    """
    assert SCHEMA_VERSION >= 6


def test_tags_text_haengt_hinten_an_der_spaltenliste():
    """Hinten: sonst verschöben sich Fundstellen-Index und bm25-Gewichte
    aller bestehenden Spalten."""
    assert FTS_COLUMNS[-1] == "tags_text"
    assert FTS_COLUMNS[:5] == [
        "filename",
        "document_type",
        "extracted_data",
        "document_text",
        "notes",
    ]


def test_fuer_jede_indexspalte_gibt_es_ein_gewicht():
    assert len(_BM25_WEIGHTS.split(",")) == len(FTS_COLUMNS)


def test_fundstelle_zeigt_weiterhin_auf_den_volltext():
    assert FTS_COLUMNS[_SNIPPET_COLUMN] == "document_text"


# --- tags_text folgt den Zuordnungen ----------------------------------


def test_setzen_schreibt_die_namen_mit():
    doc = _dokument()

    set_document_tags(doc, ["Knie-OP", "MRT"])

    text = _tags_text(doc)
    assert "Knie-OP" in text and "MRT" in text


def test_entfernen_raeumt_den_text_mit_ab():
    doc = _dokument()
    set_document_tags(doc, ["Knie-OP"])

    set_document_tags(doc, [])

    assert _tags_text(doc) == ""


def test_stapelvergabe_und_stapelentfernen_ziehen_nach():
    erstes = _dokument("a.pdf")
    zweites = _dokument("b.pdf")

    add_tag_to_documents([erstes, zweites], "Knie-OP")

    assert "Knie-OP" in _tags_text(erstes)
    assert "Knie-OP" in _tags_text(zweites)

    remove_tag_from_documents([zweites], "Knie-OP")

    assert "Knie-OP" in _tags_text(erstes)
    assert _tags_text(zweites) == ""


# --- Suche -------------------------------------------------------------


def test_volltextsuche_findet_ueber_den_tagnamen():
    """Der Zweck der ganzen Spalte: „knie" ins Suchfeld tippen genügt."""
    getaggt = _dokument("a.pdf")
    _dokument("b.pdf")

    set_document_tags(getaggt, ["Knie-OP"])

    treffer = {row["id"] for row in search_documents("Knie-OP")}

    assert treffer == {getaggt}


def test_suche_findet_auch_bei_anderer_schreibweise():
    doc = _dokument()
    set_document_tags(doc, ["Knie-OP"])

    assert {row["id"] for row in search_documents("knie")} == {doc}


def test_tagtreffer_steht_vor_dem_blossen_textreffer():
    """Ein Tag ist die einzige bewusst vergebene Angabe — wer danach sucht,
    meint es. Am Bestand gemessen ging es mit einem kleineren Gewicht
    zwischen den Textfundstellen unter."""
    nur_im_text = _dokument("a.pdf", text="Hier steht Kniegelenk im Fliesstext.")
    getaggt = _dokument("b.pdf", text="Ein ganz anderer Text.")

    set_document_tags(getaggt, ["Knie"])

    treffer = [row["id"] for row in search_documents("Knie")]

    assert treffer[0] == getaggt
    assert nur_im_text in treffer


def test_entfernter_tag_wird_nicht_mehr_gefunden():
    """Ohne Nachziehen des Index bliebe das Dokument auffindbar."""
    doc = _dokument()
    set_document_tags(doc, ["Knie-OP"])
    assert search_documents("Knie-OP")

    set_document_tags(doc, [])

    assert search_documents("Knie-OP") == []


# --- Migration eines Bestands ohne die Spalte -------------------------


def test_bestehende_zuordnungen_werden_nachgetragen():
    """Eine Datenbank aus Schritt 1/2 kennt tags_text nicht. Ohne Nachtrag
    fände die Suche vorhandene Tags nie — und niemand käme darauf, warum."""
    doc = _dokument()
    set_document_tags(doc, ["Knie-OP"])

    # Zustand vor der Erweiterung nachstellen.
    with open_connection() as conn:
        conn.execute("UPDATE documents SET tags_text = NULL")
        conn.execute("PRAGMA user_version = 5")
        conn.commit()

    init_database()

    assert "Knie-OP" in _tags_text(doc)
    assert {row["id"] for row in search_documents("Knie-OP")} == {doc}


def test_dokumente_ohne_tags_bekommen_einen_leeren_text():
    """Sonst bliebe die Spalte NULL und der Nachtrag liefe bei jedem Start
    erneut über den ganzen Bestand."""
    doc = _dokument()

    with open_connection() as conn:
        conn.execute("UPDATE documents SET tags_text = NULL")
        conn.commit()

    init_database()

    assert _tags_text(doc) == ""


# --- Anzeige in der Liste ---------------------------------------------


def test_zeilen_tragen_die_tags_mit_farbe():
    doc = _dokument()
    set_document_tags(doc, ["Knie-OP", "MRT"])

    zeile = next(row for row in build_table_rows(list_documents()) if row["id"] == doc)

    # Der Dienst liefert die Farb-NUMMER; welche Farbe daraus wird,
    # entscheidet die Seite — die Dienstschicht kennt keine Palette.
    assert [tag["name"] for tag in zeile["tags"]] == ["Knie-OP", "MRT"]
    assert all(isinstance(tag["color_index"], int) for tag in zeile["tags"])


def test_zeilen_ohne_tags_tragen_eine_leere_liste():
    doc = _dokument()

    zeile = next(row for row in build_table_rows(list_documents()) if row["id"] == doc)

    assert zeile["tags"] == []


def test_eine_abfrage_fuer_alle_zeilen(monkeypatch):
    """Bei langen Listen darf nicht je Zeile nachgefragt werden (N+1)."""
    from src.services import tag_service

    ids = [_dokument(f"{i}.pdf") for i in range(5)]
    add_tag_to_documents(ids, "Knie-OP")

    dokumente = list_documents()
    aufrufe = []
    echte_funktion = tag_service.tags_by_documents

    def zaehlend(document_ids):
        aufrufe.append(list(document_ids))

        return echte_funktion(document_ids)

    monkeypatch.setattr(tag_service, "tags_by_documents", zaehlend)

    zeilen = build_table_rows(dokumente)

    assert len(aufrufe) == 1
    assert len(aufrufe[0]) == 5
    assert all(zeile["tags"] for zeile in zeilen)

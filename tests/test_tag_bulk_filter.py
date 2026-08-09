"""Tags, Schritt 2: Stapelvergabe aus der Liste und Filtern danach.

Der Grund für diese Reihenfolge: solange Tags nur einzeln in der
Detailansicht vergeben werden können, bleibt das Feature auf Neuzugängen
sitzen — einen gewachsenen Bestand geht niemand Dokument für Dokument
durch. Erst die Stapelvergabe macht ihn erreichbar, und erst der Filter
macht das Ergebnis sichtbar.

Der Filter gilt bewusst quer über alle Kategorien: genau das können Tags,
was eine Kategorie nicht kann.
"""

import pytest
from nicegui.testing import User

from src.core.app_home import reset_profile_cache
from src.database.document_repository import insert_document
from src.database.init_database import init_database
from src.database.list_documents import list_documents
from src.services import import_job
from src.services.document_service import filter_documents
from src.services.tag_service import (
    add_tag_to_documents,
    document_ids_with_all_tags,
    remove_tag_from_documents,
    set_document_tags,
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


def _dokument(dateiname, typ="health", **felder):
    daten = {"issuer": "Musterpraxis", "document_date": "12.03.2026", **felder}

    return insert_document(
        dateiname, f"archive/2026/Gesundheit/{dateiname}", typ, daten
    )


# --- Stapelvergabe -----------------------------------------------------


def test_ein_tag_an_viele_dokumente():
    ids = [_dokument(f"{i}.pdf") for i in range(3)]

    geaendert = add_tag_to_documents(ids, "Knie-OP")

    assert geaendert == 3

    for document_id in ids:
        assert [tag["name"] for tag in tags_for_document(document_id)] == ["Knie-OP"]


def test_stapelvergabe_legt_ein_neues_tag_an():
    from src.services.tag_service import list_tags

    ids = [_dokument("a.pdf")]

    add_tag_to_documents(ids, "  Umzug 2026 ")

    assert [tag["name"] for tag in list_tags()] == ["Umzug 2026"]


def test_vorhandene_zuordnung_wird_nicht_doppelt_angelegt():
    doc = _dokument("a.pdf")
    set_document_tags(doc, ["Auto"])

    geaendert = add_tag_to_documents([doc], "Auto")

    assert geaendert == 0
    assert len(tags_for_document(doc)) == 1


def test_stapelvergabe_ignoriert_die_schreibweise():
    """Sonst entstünde neben „Auto" ein zweites Tag „auto"."""
    doc = _dokument("a.pdf")
    set_document_tags(doc, ["Auto"])
    anderes = _dokument("b.pdf")

    add_tag_to_documents([anderes], "AUTO")

    from src.services.tag_service import list_tags

    assert [tag["name"] for tag in list_tags()] == ["Auto"]
    assert [tag["name"] for tag in tags_for_document(anderes)] == ["Auto"]


def test_bestehende_tags_der_dokumente_bleiben_erhalten():
    doc = _dokument("a.pdf")
    set_document_tags(doc, ["MRT"])

    add_tag_to_documents([doc], "Knie-OP")

    assert sorted(tag["name"] for tag in tags_for_document(doc)) == ["Knie-OP", "MRT"]


def test_entfernen_trifft_nur_die_ausgewaehlten():
    behalten = _dokument("a.pdf")
    entfernen = _dokument("b.pdf")
    add_tag_to_documents([behalten, entfernen], "Auto")

    geaendert = remove_tag_from_documents([entfernen], "auto")

    assert geaendert == 1
    assert tags_for_document(entfernen) == []
    assert [tag["name"] for tag in tags_for_document(behalten)] == ["Auto"]


def test_entfernen_eines_unbekannten_tags_ist_folgenlos():
    doc = _dokument("a.pdf")

    assert remove_tag_from_documents([doc], "gibt-es-nicht") == 0


def test_entfernen_loescht_das_tag_nicht_aus_dem_vokabular():
    """Aufräumen ist Sache der Verwaltung, kein Nebeneffekt."""
    from src.services.tag_service import list_tags

    doc = _dokument("a.pdf")
    add_tag_to_documents([doc], "Auto")

    remove_tag_from_documents([doc], "Auto")

    assert [tag["name"] for tag in list_tags()] == ["Auto"]


def test_leere_eingabe_wird_abgewiesen():
    doc = _dokument("a.pdf")

    with pytest.raises(ValueError):
        add_tag_to_documents([doc], "   ")


# --- Filtern -----------------------------------------------------------


def test_mehrere_tags_gelten_zusammen():
    beide = _dokument("a.pdf")
    nur_eines = _dokument("b.pdf")
    keines = _dokument("c.pdf")

    set_document_tags(beide, ["Knie-OP", "MRT"])
    set_document_tags(nur_eines, ["Knie-OP"])

    treffer = document_ids_with_all_tags(["Knie-OP", "MRT"])

    assert treffer == {beide}
    assert keines not in treffer


def test_filter_ist_unabhaengig_von_der_schreibweise():
    doc = _dokument("a.pdf")
    set_document_tags(doc, ["Knie-OP"])

    assert document_ids_with_all_tags(["knie-op"]) == {doc}


def test_unbekanntes_tag_liefert_keine_treffer():
    _dokument("a.pdf")

    assert document_ids_with_all_tags(["gibt-es-nicht"]) == set()


def test_filter_greift_ueber_kategorien_hinweg():
    """Der eigentliche Gewinn: ein Tag haelt zusammen, was in verschiedenen
    Kategorien liegt."""
    befund = _dokument("a.pdf", typ="health")
    rechnung = _dokument("b.pdf", typ="invoice", amount=49.9)
    fremd = _dokument("c.pdf", typ="invoice", amount=10.0)

    add_tag_to_documents([befund, rechnung], "Knie-OP")

    gefiltert = filter_documents(list_documents(), tags=["Knie-OP"])

    assert {row["id"] for row in gefiltert} == {befund, rechnung}
    assert fremd not in {row["id"] for row in gefiltert}


def test_ohne_tagfilter_bleibt_die_liste_unveraendert():
    _dokument("a.pdf")
    _dokument("b.pdf")

    assert len(filter_documents(list_documents(), tags=None)) == 2
    assert len(filter_documents(list_documents(), tags=[])) == 2


def test_tagfilter_kombiniert_sich_mit_der_kategorie():
    befund = _dokument("a.pdf", typ="health")
    rechnung = _dokument("b.pdf", typ="invoice", amount=49.9)
    add_tag_to_documents([befund, rechnung], "Knie-OP")

    gefiltert = filter_documents(
        list_documents(), document_type="invoice", tags=["Knie-OP"]
    )

    assert {row["id"] for row in gefiltert} == {rechnung}


# --- Oberflaeche -------------------------------------------------------


@pytest.mark.asyncio
async def test_ohne_tags_zeigt_die_filterleiste_kein_tagfeld(user: User):
    """Wer keine Tags benutzt, soll den Filter auch nicht sehen."""
    _dokument("a.pdf")

    await user.open("/dokumente")

    await user.should_not_see(marker="tag-filter")


@pytest.mark.asyncio
async def test_mit_tags_erscheint_das_tagfeld(user: User):
    doc = _dokument("a.pdf")
    set_document_tags(doc, ["Knie-OP"])

    await user.open("/dokumente")

    await user.should_see(marker="tag-filter")


@pytest.mark.asyncio
async def test_gesetzter_tagfilter_engt_die_liste_ein(user: User, monkeypatch):
    """Durch die Oberfläche gemessen, nicht nur im Dienst. Der Filterzustand
    ist modulglobal — derselbe Weg, den die Suchtests schon benutzen."""
    from src.frontend.pages import documents as documents_page

    getaggt = _dokument("a.pdf", typ="health")
    auch_getaggt = _dokument("b.pdf", typ="invoice", amount=49.9,
                             issuer="Musterklinik")
    ohne = _dokument("c.pdf", typ="invoice", amount=10.0, issuer="Musterfremd")

    add_tag_to_documents([getaggt, auch_getaggt], "Knie-OP")
    set_document_tags(ohne, ["Auto"])

    monkeypatch.setitem(documents_page._FILTER_STATE, "tags", ["Knie-OP"])

    await user.open("/dokumente")

    # Über den Zähler geprüft, nicht über Zellinhalte: die Zeilen einer
    # Quasar-Tabelle sind für den Simulator keine eigenen Elemente — eine
    # Zusicherung darauf wäre grün-blind.
    await user.should_see("2 Dokumente gefunden")

    monkeypatch.setitem(documents_page._FILTER_STATE, "tags", ["Auto"])
    await user.open("/dokumente")
    await user.should_see("1 Dokumente gefunden")


# Die Stapelvergabe selbst hat hier bewusst KEINEN Oberflächentest: die
# Auswahlleiste ist erst sichtbar, wenn Zeilen ausgewählt sind, und eine
# Auswahl kann der Simulator nicht herstellen — die Häkchen der Tabelle
# gehören Quasar, nicht NiceGUI. Geprüft wird deshalb, was sie tut (die
# Dienst-Tests oben); dieselbe Aufteilung wie bei den übrigen
# Stapelaktionen in test_bulk_actions.py, das ganz ohne Oberfläche auskommt.

"""Tags, Schritt 4: umbenennen, zusammenführen, löschen, Farbe.

Zusammenführen ist die Pflichtfunktion, nicht die Kür: die App fängt
Groß-/Kleinschreibung ab, aber „Knie OP" gegen „Knie-OP" kann sie nicht
erraten — und ohne Zusammenführen wäre der erste Tippfehler dauerhaft.

Die stille Gefahr bei allen vier Operationen ist der Suchindex: er hängt an
`documents.tags_text`. Wer ein Tag umbenennt und die Spalte nicht nachzieht,
findet es danach unter dem alten Namen — und unter dem neuen gar nicht.
Deshalb prüft hier jede Operation auch die Suche.
"""

import pytest
from nicegui.testing import User

from src.core.app_home import reset_profile_cache
from src.database.document_repository import insert_document
from src.database.init_database import init_database
from src.database.search import search_documents
from src.services import import_job
from src.services.tag_service import (
    add_tag_to_documents,
    delete_tag,
    list_tags,
    merge_tags,
    rename_tag,
    set_tag_color,
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


def _dokument(dateiname="a.pdf"):
    return insert_document(
        dateiname,
        f"archive/2026/Gesundheit/{dateiname}",
        "health",
        {"issuer": "Musterpraxis", "document_date": "12.03.2026"},
        document_text="Erfundener Text.",
    )


def _id_von(name):
    return next(tag["id"] for tag in list_tags() if tag["name"] == name)


def _namen():
    return [tag["name"] for tag in list_tags()]


# --- Umbenennen --------------------------------------------------------


def test_umbenennen_aendert_namen_und_suche():
    doc = _dokument()
    add_tag_to_documents([doc], "Knie OP")

    rename_tag(_id_von("Knie OP"), "Knie-OP")

    assert _namen() == ["Knie-OP"]
    assert [tag["name"] for tag in tags_for_document(doc)] == ["Knie-OP"]
    assert {row["id"] for row in search_documents("Knie-OP")} == {doc}


def test_unter_dem_alten_namen_wird_nichts_mehr_gefunden():
    """Ohne Nachziehen von tags_text bliebe der alte Name auffindbar."""
    doc = _dokument()
    add_tag_to_documents([doc], "Kniee")

    rename_tag(_id_von("Kniee"), "Knie")

    assert search_documents("Kniee") == []


def test_schreibweise_darf_geaendert_werden():
    """Gleicher Schlüssel, andere Schreibweise — das ist kein Konflikt,
    sondern genau der Zweck des Umbenennens."""
    doc = _dokument()
    add_tag_to_documents([doc], "knie-op")

    rename_tag(_id_von("knie-op"), "Knie-OP")

    assert _namen() == ["Knie-OP"]


def test_umbenennen_auf_ein_vorhandenes_tag_wird_abgewiesen():
    """Zwei Tags mit demselben Schlüssel darf es nicht geben — dafür ist
    Zusammenführen da, und die Meldung sagt das auch."""
    doc = _dokument()
    add_tag_to_documents([doc], "Auto")
    add_tag_to_documents([doc], "Fahrrad")

    with pytest.raises(ValueError, match="zusammenführen|Zusammenführen"):
        rename_tag(_id_von("Fahrrad"), "auto")


def test_leerer_name_wird_abgewiesen():
    doc = _dokument()
    add_tag_to_documents([doc], "Auto")

    with pytest.raises(ValueError):
        rename_tag(_id_von("Auto"), "   ")


# --- Zusammenführen ----------------------------------------------------


def test_zusammenfuehren_zieht_die_dokumente_um():
    erstes = _dokument("a.pdf")
    zweites = _dokument("b.pdf")
    add_tag_to_documents([erstes], "Knie-OP")
    add_tag_to_documents([zweites], "Knie OP")

    bewegt = merge_tags(_id_von("Knie OP"), _id_von("Knie-OP"))

    assert bewegt == 1
    assert _namen() == ["Knie-OP"]
    assert [tag["name"] for tag in tags_for_document(zweites)] == ["Knie-OP"]


def test_zusammenfuehren_erzeugt_keine_doppelte_zuordnung():
    """Ein Dokument, das BEIDE Tags trägt, darf danach nicht zwei gleiche
    Zuordnungen haben."""
    doc = _dokument()
    add_tag_to_documents([doc], "Knie-OP")
    add_tag_to_documents([doc], "Knie OP")

    merge_tags(_id_von("Knie OP"), _id_von("Knie-OP"))

    assert [tag["name"] for tag in tags_for_document(doc)] == ["Knie-OP"]


def test_zusammenfuehren_zieht_die_suche_nach():
    erstes = _dokument("a.pdf")
    zweites = _dokument("b.pdf")
    add_tag_to_documents([erstes], "Knie-OP")
    add_tag_to_documents([zweites], "Knie OP")

    merge_tags(_id_von("Knie OP"), _id_von("Knie-OP"))

    assert {row["id"] for row in search_documents("Knie-OP")} == {erstes, zweites}
    assert search_documents("Knie OP") == []


def test_zusammenfuehren_mit_sich_selbst_wird_abgewiesen():
    doc = _dokument()
    add_tag_to_documents([doc], "Auto")
    eigenes = _id_von("Auto")

    with pytest.raises(ValueError):
        merge_tags(eigenes, eigenes)


def test_zusammenfuehren_eines_unbekannten_tags_wird_abgewiesen():
    doc = _dokument()
    add_tag_to_documents([doc], "Auto")

    with pytest.raises(ValueError):
        merge_tags(999, _id_von("Auto"))


# --- Löschen -----------------------------------------------------------


def test_loeschen_nimmt_das_tag_und_seine_zuordnungen():
    doc = _dokument()
    add_tag_to_documents([doc], "Auto")

    betroffen = delete_tag(_id_von("Auto"))

    assert betroffen == 1
    assert list_tags() == []
    assert tags_for_document(doc) == []
    assert search_documents("Auto") == []


def test_loeschen_laesst_die_anderen_tags_stehen():
    doc = _dokument()
    add_tag_to_documents([doc], "Auto")
    add_tag_to_documents([doc], "Knie-OP")

    delete_tag(_id_von("Auto"))

    assert [tag["name"] for tag in tags_for_document(doc)] == ["Knie-OP"]


def test_verwaistes_tag_laesst_sich_loeschen():
    doc = _dokument()
    add_tag_to_documents([doc], "Auto")
    delete_tag_id = _id_von("Auto")
    from src.services.tag_service import remove_tag_from_documents

    remove_tag_from_documents([doc], "Auto")

    assert [tag["usage"] for tag in list_tags()] == [0]
    assert delete_tag(delete_tag_id) == 0
    assert list_tags() == []


# --- Farbe -------------------------------------------------------------


def test_farbe_laesst_sich_setzen():
    doc = _dokument()
    add_tag_to_documents([doc], "Auto")

    set_tag_color(_id_von("Auto"), 3)

    assert [tag["color_index"] for tag in list_tags()] == [3]


def test_unsinnige_farbnummer_wird_abgewiesen():
    doc = _dokument()
    add_tag_to_documents([doc], "Auto")

    with pytest.raises(ValueError):
        set_tag_color(_id_von("Auto"), -1)


# --- Oberfläche --------------------------------------------------------


@pytest.mark.asyncio
async def test_einstellungen_haben_einen_tag_reiter(user: User):
    doc = _dokument()
    add_tag_to_documents([doc], "Knie-OP")

    await user.open("/einstellungen")

    await user.should_see("Tags")


@pytest.mark.asyncio
async def test_ohne_tags_erklaert_der_reiter_sich_selbst(user: User):
    await user.open("/einstellungen")
    user.find("Tags").click()

    await user.should_see(marker="tag-verwaltung-leer")


@pytest.mark.asyncio
async def test_verwaltung_zeigt_tag_und_nutzung(user: User):
    erstes = _dokument("a.pdf")
    zweites = _dokument("b.pdf")
    add_tag_to_documents([erstes, zweites], "Knie-OP")

    await user.open("/einstellungen")
    user.find("Tags").click()

    await user.should_see("Knie-OP")
    await user.should_see(marker=f"tag-nutzung-{_id_von('Knie-OP')}")


@pytest.mark.asyncio
async def test_markierungen_tragen_die_id_nicht_den_namen(user: User):
    """NiceGUI zerlegt Markierungen an Leerzeichen (Element.mark). Ein Tag
    „Knie OP" ergaebe mit dem Namen zwei Marken — davon eine streunende
    namens „OP", die irgendein anderes Element mittreffen koennte."""
    doc = _dokument()
    add_tag_to_documents([doc], "Knie OP")
    tag_id = _id_von("Knie OP")

    await user.open("/einstellungen")
    user.find("Tags").click()

    await user.should_see(marker=f"tag-nutzung-{tag_id}")
    await user.should_not_see(marker="OP")

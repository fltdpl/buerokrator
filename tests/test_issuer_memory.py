"""Aussteller-Gedächtnis: was der geprüfte Bestand über einen Aussteller weiß.

Grundlage ist der bereits extrahierte Aussteller des Dokuments, nicht sein
Rohtext. Gezählt werden ausschließlich geprüfte Dokumente.

Alle Namen und Werte erfunden.
"""

import src.database.database as database
from src.database.document_repository import insert_document
from src.database.set_document_verified import set_document_verified
from src.services.issuer_memory import type_memory, type_mismatch


def _setup_project(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "\n".join(
            [
                "paths:",
                f"  inbox: {tmp_path / 'inbox'}",
                f"  archive: {tmp_path / 'archive'}",
                "database:",
                f"  path: {tmp_path / 'database' / 'test.db'}",
                "archive:",
                "  category_mapping:",
                "    invoice: Rechnungen",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(database, "_schema_ready", False)


def _insert(filename, data, document_type="invoice", verified=1):
    document_id = insert_document(
        filename=filename,
        archive_path=f"archive/2024/Rechnungen/{filename}",
        document_type=document_type,
        extracted_data=data,
    )

    if verified:
        set_document_verified(document_id, True)

    return document_id


# --- Typ-Gedächtnis ---------------------------------------------------------


def test_type_memory_zaehlt_die_typen_des_ausstellers(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    _insert("a.pdf", {"issuer": "Musterkasse"}, document_type="pension")
    _insert("b.pdf", {"issuer": "Musterkasse"}, document_type="pension")
    _insert("c.pdf", {"issuer": "Musterkasse"}, document_type="insurance")

    gedaechtnis = type_memory("Musterkasse")

    assert gedaechtnis["document_type"] == "pension"
    assert gedaechtnis["counts"] == {"pension": 2, "insurance": 1}
    assert gedaechtnis["total"] == 3


def test_type_memory_kennt_den_aussteller_nicht(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    assert type_memory("Fremdfirma AG") is None


def test_type_memory_ignoriert_ein_bestimmtes_dokument(tmp_path, monkeypatch):
    # Beim Prüfen eines Dokuments darf es sich nicht selbst bestätigen.
    _setup_project(tmp_path, monkeypatch)
    eigenes = _insert("a.pdf", {"issuer": "Musterkasse"}, document_type="insurance")

    assert type_memory("Musterkasse", exclude_id=eigenes) is None


def test_type_memory_zaehlt_nur_geprufte_dokumente(tmp_path, monkeypatch):
    # Ungeprüfte Dokumente tragen möglicherweise einen Erkennungsfehler im
    # Aussteller. Würde er ins Gedächtnis wandern, verfestigte er sich.
    _setup_project(tmp_path, monkeypatch)
    _insert("a.pdf", {"issuer": "Musterkasse"}, verified=0)

    assert type_memory("Musterkasse") is None


def test_type_memory_loest_aliase_auf(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    from src.organizer import issuer_normalizer

    (tmp_path / "aussteller_aliase.yaml").write_text(
        "Musterkasse:\n  - Musterkasse AG\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        issuer_normalizer, "aliases_path", lambda: tmp_path / "aussteller_aliase.yaml"
    )
    monkeypatch.setattr(issuer_normalizer, "_cache", {"key": None, "value": ({}, ())})

    _insert("a.pdf", {"issuer": "Musterkasse AG"}, document_type="pension")

    assert type_memory("Musterkasse")["document_type"] == "pension"


def test_arbeitgeber_zaehlt_als_aussteller(tmp_path, monkeypatch):
    # employment-Dokumente tragen den Namen in "employer" — gleiche Auflösung
    # wie in Liste, Filter und Dubletten-Prüfung.
    _setup_project(tmp_path, monkeypatch)
    _insert(
        "a.pdf", {"employer": "Musterfirma GmbH"}, document_type="employment"
    )

    assert type_memory("Musterfirma GmbH")["total"] == 1


# --- Plausibilitäts-Hinweis -------------------------------------------------


def test_abweichung_von_einheitlichem_aussteller_wird_gemeldet(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    _insert("a.pdf", {"issuer": "Musterkasse"}, document_type="pension")
    _insert("b.pdf", {"issuer": "Musterkasse"}, document_type="pension")
    abweichend = _insert(
        "c.pdf", {"issuer": "Musterkasse"}, document_type="insurance"
    )

    hinweis = type_mismatch(abweichend)

    assert hinweis["expected_type"] == "pension"
    assert hinweis["document_type"] == "insurance"
    assert hinweis["total"] == 2
    assert hinweis["issuer"] == "Musterkasse"


def test_gemischter_aussteller_loest_keinen_hinweis_aus(tmp_path, monkeypatch):
    # Der Fall, der die Regel trägt: manche Anbieter liefern legitim mehrere
    # Typen (Vorsorge UND Versicherung). Dort ist eine Abweichung nichts
    # Besonderes — am Bestand gemessen macht genau diese Bedingung den
    # Unterschied zwischen brauchbar und Lärm.
    _setup_project(tmp_path, monkeypatch)
    _insert("a.pdf", {"issuer": "Musterkasse"}, document_type="pension")
    _insert("b.pdf", {"issuer": "Musterkasse"}, document_type="insurance")
    weiteres = _insert("c.pdf", {"issuer": "Musterkasse"}, document_type="insurance")

    assert type_mismatch(weiteres) is None


def test_passender_typ_loest_keinen_hinweis_aus(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    _insert("a.pdf", {"issuer": "Musterkasse"}, document_type="pension")
    _insert("b.pdf", {"issuer": "Musterkasse"}, document_type="pension")
    passend = _insert("c.pdf", {"issuer": "Musterkasse"}, document_type="pension")

    assert type_mismatch(passend) is None


def test_ein_einzelnes_vordokument_reicht_nicht(tmp_path, monkeypatch):
    # „Ausnahmslos" ist bei einem einzigen Vordokument keine Aussage.
    _setup_project(tmp_path, monkeypatch)
    _insert("a.pdf", {"issuer": "Musterkasse"}, document_type="pension")
    abweichend = _insert(
        "b.pdf", {"issuer": "Musterkasse"}, document_type="insurance"
    )

    assert type_mismatch(abweichend) is None


def test_unbekannter_aussteller_loest_keinen_hinweis_aus(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    allein = _insert("a.pdf", {"issuer": "Fremdfirma AG"}, document_type="invoice")

    assert type_mismatch(allein) is None


def test_dokument_ohne_aussteller_loest_keinen_hinweis_aus(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    ohne = _insert("a.pdf", {}, document_type="invoice")

    assert type_mismatch(ohne) is None


def test_hinweis_fuer_unbekanntes_dokument(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    assert type_mismatch(999) is None


def test_ungeprufte_vordokumente_loesen_keinen_hinweis_aus(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)
    _insert("a.pdf", {"issuer": "Musterkasse"}, document_type="pension", verified=0)
    _insert("b.pdf", {"issuer": "Musterkasse"}, document_type="pension", verified=0)
    abweichend = _insert(
        "c.pdf", {"issuer": "Musterkasse"}, document_type="insurance"
    )

    assert type_mismatch(abweichend) is None

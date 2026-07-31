"""Inhaltliche Dubletten-Warnung.

Anlass: derselbe Beleg lag mehrfach im Bestand — verschiedene Scans, also
verschiedene Bytes, also greift der Inhalts-Hash nicht. Hier wird nicht der
Bytestand verglichen, sondern der erkannte Inhalt.

Alle Werte erfunden.
"""

import src.database.database as database
from src.database.document_repository import insert_document
from src.services.duplicate_service import find_content_duplicates


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


def _insert(filename, data, document_type="invoice"):
    return insert_document(
        filename=filename,
        archive_path=f"archive/2024/Rechnungen/{filename}",
        document_type=document_type,
        extracted_data=data,
    )


def test_gleicher_aussteller_betrag_und_datum_gilt_als_dublette(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    erster = _insert(
        "2024-03-11_Musterversand_42EUR.pdf",
        {"issuer": "Musterversand", "amount": 42.5, "document_date": "11.03.2024"},
    )
    zweiter = _insert(
        "2024-03-11_Musterversand_42EUR (1).pdf",
        {"issuer": "Musterversand", "amount": 42.5, "document_date": "11.03.2024"},
    )

    treffer = find_content_duplicates(zweiter)

    assert [eintrag["id"] for eintrag in treffer] == [erster]
    assert treffer[0]["filename"] == "2024-03-11_Musterversand_42EUR.pdf"
    assert "Betrag" in treffer[0]["reason"]


def test_gleiche_rechnungsnummer_reicht_auch_ohne_betrag(tmp_path, monkeypatch):
    # Der zweite Scan hat einen unlesbaren Betrag — die Rechnungsnummer
    # identifiziert den Beleg trotzdem eindeutig.
    _setup_project(tmp_path, monkeypatch)

    erster = _insert(
        "2024-03-11_Musterversand_RE-1001.pdf",
        {
            "issuer": "Musterversand",
            "invoice_number": "RE-1001",
            "amount": 42.5,
            "document_date": "11.03.2024",
        },
    )
    zweiter = _insert(
        "2024-03-11_Musterversand_RE-1001_scan.pdf",
        {"issuer": "Musterversand", "invoice_number": "RE-1001"},
    )

    treffer = find_content_duplicates(zweiter)

    assert [eintrag["id"] for eintrag in treffer] == [erster]
    assert "Rechnungsnummer" in treffer[0]["reason"]


def test_anderer_aussteller_ist_keine_dublette(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    _insert(
        "2024-03-11_Musterversand.pdf",
        {"issuer": "Musterversand", "amount": 42.5, "document_date": "11.03.2024"},
    )
    zweiter = _insert(
        "2024-03-11_Musterhandel.pdf",
        {"issuer": "Musterhandel", "amount": 42.5, "document_date": "11.03.2024"},
    )

    assert find_content_duplicates(zweiter) == []


def test_gleicher_aussteller_aber_anderes_datum_ist_keine_dublette(
    tmp_path, monkeypatch
):
    # Der Normalfall bei einem Abo: gleicher Anbieter, gleicher Betrag,
    # anderer Monat. Das darf keine Warnung auslösen.
    _setup_project(tmp_path, monkeypatch)

    _insert(
        "2024-03-01_Musterversand.pdf",
        {"issuer": "Musterversand", "amount": 19.9, "document_date": "01.03.2024"},
    )
    zweiter = _insert(
        "2024-04-01_Musterversand.pdf",
        {"issuer": "Musterversand", "amount": 19.9, "document_date": "01.04.2024"},
    )

    assert find_content_duplicates(zweiter) == []


def test_leere_felder_matchen_nie(tmp_path, monkeypatch):
    # Analog zum NULL-Hash: unerkannte Werte dürfen nicht den halben
    # Bestand als Dublette markieren.
    _setup_project(tmp_path, monkeypatch)

    _insert("leer_a.pdf", {})
    _insert("leer_b.pdf", {"issuer": "", "amount": None, "document_date": ""})
    dritter = _insert("leer_c.pdf", {"issuer": "", "invoice_number": ""})

    assert find_content_duplicates(dritter) == []


def test_betragsformat_und_gross_kleinschreibung_stoeren_nicht(tmp_path, monkeypatch):
    # Zwei Scans desselben Belegs, unterschiedlich erkannt: deutsches
    # Betragsformat als Text, Aussteller anders geschrieben, Datum
    # vierstellig vs. zweistellig im Jahr.
    _setup_project(tmp_path, monkeypatch)

    erster = _insert(
        "a.pdf",
        {"issuer": "Musterversand", "amount": 1234.56, "document_date": "11.03.2024"},
    )
    zweiter = _insert(
        "b.pdf",
        {
            "issuer": "  musterversand ",
            "amount": "1.234,56",
            "document_date": "11.03.24",
        },
    )

    assert [eintrag["id"] for eintrag in find_content_duplicates(zweiter)] == [erster]


def test_dokument_findet_sich_nicht_selbst(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    einziges = _insert(
        "allein.pdf",
        {"issuer": "Musterversand", "amount": 42.5, "document_date": "11.03.2024"},
    )

    assert find_content_duplicates(einziges) == []


def test_unbekanntes_dokument_liefert_leere_liste(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    assert find_content_duplicates(999) == []


def test_mehrere_treffer_kommen_aufsteigend_nach_id(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    beleg = {"issuer": "Musterversand", "amount": 42.5, "document_date": "11.03.2024"}
    erster = _insert("a.pdf", dict(beleg))
    zweiter = _insert("b.pdf", dict(beleg))
    dritter = _insert("c.pdf", dict(beleg))

    treffer = find_content_duplicates(dritter)

    assert [eintrag["id"] for eintrag in treffer] == [erster, zweiter]


def test_aussteller_alias_vereint_schreibweisen(tmp_path, monkeypatch):
    # Zwei Scans, vom LLM verschieden benannt. Die gepflegte Alias-Datei
    # führt beide auf denselben kanonischen Namen — dann ist es dieselbe
    # Rechnung.
    _setup_project(tmp_path, monkeypatch)

    from src.organizer import issuer_normalizer

    (tmp_path / "aussteller_aliase.yaml").write_text(
        "Musterversand:\n  - Musterversand GmbH\n  - Musterversand Handel\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        issuer_normalizer, "aliases_path", lambda: tmp_path / "aussteller_aliase.yaml"
    )
    monkeypatch.setattr(issuer_normalizer, "_cache", {"key": None, "value": ({}, ())})

    erster = _insert(
        "a.pdf",
        {
            "issuer": "Musterversand GmbH",
            "amount": 42.5,
            "document_date": "11.03.2024",
        },
    )
    zweiter = _insert(
        "b.pdf",
        {
            "issuer": "Musterversand Handel",
            "amount": 42.5,
            "document_date": "11.03.2024",
        },
    )

    assert [eintrag["id"] for eintrag in find_content_duplicates(zweiter)] == [erster]


def test_arbeitgeber_zaehlt_als_aussteller(tmp_path, monkeypatch):
    # employment-Dokumente tragen den Namen in "employer" — die gleiche
    # Auflösung wie in Liste und Filter.
    _setup_project(tmp_path, monkeypatch)

    erster = _insert(
        "a.pdf",
        {"employer": "Musterfirma GmbH", "amount": 100.0, "document_date": "01.02.2024"},
        document_type="employment",
    )
    zweiter = _insert(
        "b.pdf",
        {"employer": "Musterfirma GmbH", "amount": 100.0, "document_date": "01.02.2024"},
        document_type="employment",
    )

    assert [eintrag["id"] for eintrag in find_content_duplicates(zweiter)] == [erster]

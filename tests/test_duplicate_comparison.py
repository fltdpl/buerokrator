"""Gegenüberstellung zweier Dokumente, die als Dublette gemeldet wurden.

Der Hinweis nannte bisher nur die NAMEN der widersprechenden Felder. Daran
entscheidet sich aber nichts: "RE-4471" gegen "RE-4477" ist ein OCR-Verleser
und spricht FÜR eine Dublette, "RE-4471" gegen "RE-9002" sind zwei Belege.
Dieselbe Meldung, gegenteilige Antwort — deshalb müssen die Werte selbst
nebeneinander stehen.

Gezeigt wird der ROHWERT aus dem Dokument, verglichen wird über denselben
Schlüssel wie in der Erkennung (Alias, Betragsformat, Datumsschreibweise).
Sonst stünde da ein normalisierter Wert, den niemand im PDF wiederfindet.

Alle Werte erfunden.
"""

import src.database.database as database
from src.database.document_repository import insert_document
from src.services.duplicate_service import compare_documents


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


def _zeile(vergleich, label):
    for eintrag in vergleich:
        if eintrag["label"] == label:
            return eintrag

    raise AssertionError(f"Keine Zeile {label!r} in {[e['label'] for e in vergleich]}")


def test_abweichender_wert_zeigt_beide_seiten_im_klartext(tmp_path, monkeypatch):
    """Der Kern: nicht "abweichend: Rechnungsnummer", sondern beide Nummern."""
    _setup_project(tmp_path, monkeypatch)

    links = _insert(
        "2024-03-11_Musterversand_RE-4471.pdf",
        {
            "issuer": "Musterversand GmbH",
            "amount": 148.90,
            "document_date": "11.03.2024",
            "invoice_number": "RE-4471",
        },
    )
    rechts = _insert(
        "2024-03-11_Musterversand_RE-4477.pdf",
        {
            "issuer": "Musterversand GmbH",
            "amount": 148.90,
            "document_date": "11.03.2024",
            "invoice_number": "RE-4477",
        },
    )

    zeile = _zeile(compare_documents(links, rechts), "Rechnungsnummer")

    assert zeile["links"] == "RE-4471"
    assert zeile["rechts"] == "RE-4477"
    assert zeile["status"] == "abweichend"


def test_uebereinstimmung_wird_ebenso_gezeigt(tmp_path, monkeypatch):
    """Was übereinstimmt, trägt die Entscheidung mit — nicht nur der Widerspruch."""
    _setup_project(tmp_path, monkeypatch)

    links = _insert(
        "a.pdf",
        {"issuer": "Musterversand GmbH", "amount": 148.90, "document_date": "11.03.2024"},
    )
    rechts = _insert(
        "b.pdf",
        {"issuer": "Musterversand GmbH", "amount": 148.90, "document_date": "11.03.2024"},
    )

    vergleich = compare_documents(links, rechts)

    assert _zeile(vergleich, "Aussteller")["status"] == "gleich"
    assert _zeile(vergleich, "Betrag")["status"] == "gleich"
    assert _zeile(vergleich, "Datum")["status"] == "gleich"


def test_verschiedene_schreibweise_gilt_als_gleich_zeigt_aber_beide_formen(
    tmp_path, monkeypatch
):
    """Verglichen wird normalisiert, angezeigt wird das Original.

    Sonst steht in der Tabelle ein Wert, den man im PDF nicht wiederfindet —
    und genau dort schaut der Nutzer nach.
    """
    _setup_project(tmp_path, monkeypatch)

    links = _insert("a.pdf", {"issuer": "Musterversand", "amount": "1.234,56"})
    rechts = _insert("b.pdf", {"issuer": "musterversand", "amount": 1234.56})

    vergleich = compare_documents(links, rechts)
    betrag = _zeile(vergleich, "Betrag")

    assert betrag["status"] == "gleich"
    assert betrag["links"] == "1.234,56"
    assert betrag["rechts"] != betrag["links"]
    assert _zeile(vergleich, "Aussteller")["status"] == "gleich"


def test_fehlender_wert_ist_kein_widerspruch(tmp_path, monkeypatch):
    """Eine Lücke in der Erkennung ist kein Gegenbeweis — sie heißt "fehlt".

    Als "abweichend" gezeigt würde sie gegen die Dublette sprechen, obwohl
    sie nichts aussagt.
    """
    _setup_project(tmp_path, monkeypatch)

    links = _insert("a.pdf", {"issuer": "Musterversand", "invoice_number": "RE-4471"})
    rechts = _insert("b.pdf", {"issuer": "Musterversand", "invoice_number": ""})

    zeile = _zeile(compare_documents(links, rechts), "Rechnungsnummer")

    assert zeile["status"] == "fehlt"
    assert zeile["links"] == "RE-4471"
    assert zeile["rechts"] == ""


def test_beidseitig_leere_felder_stehen_nicht_in_der_tabelle(tmp_path, monkeypatch):
    """Eine Zeile mit zwei Strichen kostet Platz und sagt nichts."""
    _setup_project(tmp_path, monkeypatch)

    links = _insert("a.pdf", {"issuer": "Musterversand", "amount": 42.0})
    rechts = _insert("b.pdf", {"issuer": "Musterversand", "amount": 42.0})

    labels = [eintrag["label"] for eintrag in compare_documents(links, rechts)]

    assert "Rechnungsnummer" not in labels
    assert "Aussteller" in labels


def test_arbeitgeber_zaehlt_als_aussteller(tmp_path, monkeypatch):
    """employment-Dokumente nennen ihn `employer` — gleiche Auflösung wie in
    der Erkennung, sonst stünde die Aussteller-Zeile dort leer."""
    _setup_project(tmp_path, monkeypatch)

    links = _insert("a.pdf", {"employer": "Musterfirma GmbH"}, document_type="employment")
    rechts = _insert("b.pdf", {"employer": "Musterfirma GmbH"}, document_type="employment")

    zeile = _zeile(compare_documents(links, rechts), "Aussteller")

    assert zeile["status"] == "gleich"
    assert zeile["links"] == "Musterfirma GmbH"


def test_unbekanntes_dokument_liefert_leere_liste(tmp_path, monkeypatch):
    _setup_project(tmp_path, monkeypatch)

    vorhanden = _insert("a.pdf", {"issuer": "Musterversand"})

    assert compare_documents(vorhanden, 9999) == []
    assert compare_documents(9999, vorhanden) == []

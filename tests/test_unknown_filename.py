"""Dateinamen für Typen ohne eigenen Bauer.

Anlass: `unknown`-Dokumente hießen schlicht `unknown.pdf` — ohne Datum, ohne
Aussteller. In der Dateiliste war nicht zu erkennen, worum es geht, und der
Kollisionszähler machte aus dem zweiten `unknown_1.pdf`.

Alle Werte erfunden.
"""

from src.organizer.filename_builder import build_filename


def _build(extracted_data, document_type="unknown"):
    return build_filename(
        {"document_type": document_type},
        extracted_data,
        "scan.pdf",
    )


def test_unknown_traegt_datum_und_aussteller_im_namen():
    name = _build(
        {
            "document_date": "11.03.2026",
            "issuer": "Musterversand GmbH",
            "subject": "Mitteilung",
        }
    )

    assert name == "2026-03-11_Musterversand_GmbH_Mitteilung.pdf"


def test_ohne_betreff_steht_der_typ_im_namen():
    # Sonst bliebe vom Dokument nur Datum und Aussteller — der Typ ist die
    # einzige Aussage, die die Klassifikation überhaupt getroffen hat.
    name = _build({"document_date": "11.03.2026", "issuer": "Musterversand"})

    assert name == "2026-03-11_Musterversand_unknown.pdf"


def test_ganz_ohne_werte_bleibt_ein_gueltiger_name():
    name = _build({})

    assert name.endswith(".pdf")
    assert name != "unknown.pdf"


def test_zwei_unknown_dokumente_bekommen_verschiedene_namen():
    erster = _build({"document_date": "11.03.2026", "issuer": "Musterversand"})
    zweiter = _build({"document_date": "12.03.2026", "issuer": "Musterhandel"})

    assert erster != zweiter


def test_unbekannter_typ_nutzt_denselben_fallback():
    # Ein künftiger Typ ohne eigenen Bauer soll nicht wieder bei einem
    # nichtssagenden Namen landen.
    name = _build(
        {"document_date": "11.03.2026", "issuer": "Musterversand"},
        document_type="sonstiges",
    )

    assert name == "2026-03-11_Musterversand_sonstiges.pdf"


def test_pfadtrenner_im_betreff_bricht_nicht_aus():
    name = _build({"document_date": "11.03.2026", "subject": "../../etc/passwd"})

    assert "/" not in name
    assert not name.startswith(".")

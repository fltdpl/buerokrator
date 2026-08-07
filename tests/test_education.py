"""Kategorie Ausbildung (education): Vokabular, Felder, Abgrenzung.

Die Abgrenzung zu employment ist der eigentliche Prüfstein: Schulen und
Hochschulen treten in einem Dokumentenbestand auch als ARBEITGEBER auf.
Deshalb steht neben jedem Positivfall eine Gegenprobe.
"""

from src.classifier.rule_classifier import match_rule
from src.core.document_display import get_document_art_label
from src.core.document_fields import (
    KNOWN_SUBTYPES,
    constrain_subtype,
    normalize_subtype,
    whitelist_fields,
)
from src.core.document_types import EDUCATION, EMPLOYMENT
from src.organizer.filename_builder import build_filename
from src.services.form_schema import EDUCATION_SUBTYPE_LABELS, form_fields
from src.tax.tax_relevance import default_tax_relevance


def test_vokabular_hat_genau_drei_unterarten():
    assert KNOWN_SUBTYPES[EDUCATION] == {"zeugnis", "fortbildung", "sonstiges"}
    assert set(EDUCATION_SUBTYPE_LABELS) == KNOWN_SUBTYPES[EDUCATION]


def test_whitelist_haelt_die_vier_felder_und_verwirft_den_rest():
    data = {
        "document_subtype": "zeugnis",
        "issuer": "Musterschule",
        "document_date": "15.06.2004",
        "subject": "Abschlusszeugnis",
        "amount": 42.0,
        "policy_number": "PN-1",
    }

    result = whitelist_fields(EDUCATION, data)

    assert result == {
        "document_subtype": "zeugnis",
        "issuer": "Musterschule",
        "document_date": "15.06.2004",
        "subject": "Abschlusszeugnis",
    }


def test_aliase_treffen_die_gaengigen_wortlaute():
    # Ohne diese Tabelle greift NUR der Fuzzy-Match (cutoff 0.85), und der
    # erkennt keinen einzigen dieser Wortlaute — alles liefe in "sonstiges".
    for wortlaut in (
        "Abschlusszeugnis",
        "Schulzeugnis",
        "Abiturzeugnis",
        "Hochschulzeugnis",
        "Bachelorzeugnis",
        "Masterurkunde",
        "Urkunde",
        "Diplom",
        "Prüfungszeugnis",
        "Immatrikulationsbescheinigung",
    ):
        assert normalize_subtype(EDUCATION, wortlaut) == "zeugnis", wortlaut

    for wortlaut in (
        "Teilnahmebescheinigung",
        "Zertifikat",
        "Weiterbildung",
        "Fortbildungsnachweis",
        "Lehrgang",
        "Seminar",
        "Schulung",
    ):
        assert normalize_subtype(EDUCATION, wortlaut) == "fortbildung", wortlaut


def test_zeugnis_alias_bleibt_typgebunden():
    # In employment zeigt "zeugnis" weiterhin auf arbeitszeugnis; die
    # Alias-Tabelle ist pro Typ verschachtelt und darf sich nicht mischen.
    assert normalize_subtype(EMPLOYMENT, "Zeugnis") == "arbeitszeugnis"
    assert normalize_subtype(EDUCATION, "Zeugnis") == "zeugnis"


def test_erfundene_unterart_faellt_auf_sonstiges_und_rettet_den_wortlaut():
    result = constrain_subtype(
        EDUCATION,
        {"document_subtype": "Sportabzeichen Gold", "subject": ""},
    )

    assert result["document_subtype"] == "sonstiges"
    assert result["subject"] == "Sportabzeichen Gold"


def test_formularfelder_ueberleben_die_whitelist():
    for subtype in EDUCATION_SUBTYPE_LABELS:
        keys = {field["key"] for field in form_fields(EDUCATION, subtype)}
        erlaubt = set(whitelist_fields(EDUCATION, dict.fromkeys(keys, "x")))

        assert keys <= erlaubt | {"document_subtype"}, subtype


def test_dateiname_traegt_datum_aussteller_und_betreff():
    name = build_filename(
        {"document_type": EDUCATION},
        {
            "document_subtype": "zeugnis",
            "issuer": "Musterschule",
            "document_date": "15.06.2004",
            "subject": "Abschlusszeugnis",
        },
        "scan.pdf",
    )

    assert name == "2004-06-15_Musterschule_Abschlusszeugnis.pdf"


def test_dateiname_faellt_auf_die_unterart_zurueck_wenn_kein_betreff_da_ist():
    name = build_filename(
        {"document_type": EDUCATION},
        {"document_subtype": "fortbildung", "issuer": "Musterakademie"},
        "scan.pdf",
    )

    assert name.endswith("_Musterakademie_Fortbildung.pdf")


def test_ausbildung_ist_nicht_steuerrelevant():
    # Kein Eintrag in tax_relevance: Zeugnisse gehören nicht in die Erklärung.
    # Die Kosten einer Fortbildung laufen über die Rechnung (invoice).
    for subtype in EDUCATION_SUBTYPE_LABELS:
        assert default_tax_relevance(EDUCATION, {"document_subtype": subtype}) is False


def test_listenlabel_zeigt_die_unterart():
    assert (
        get_document_art_label(EDUCATION, {"document_subtype": "zeugnis"})
        == "Zeugnis / Urkunde"
    )
    assert (
        get_document_art_label(
            EDUCATION,
            {"document_subtype": "sonstiges", "subject": "Sprachkurs"},
        )
        == "Sprachkurs"
    )


def test_regel_erkennt_eindeutige_titel():
    for text in (
        "Musterschule der Stadt Musterstadt\n"
        "Abiturzeugnis\n"
        "Allgemeine Hochschulreife\n",
        "Musterhochschule\n"
        "Masterurkunde\n"
        "Der Hochschulgrad Master of Science wird verliehen.\n",
    ):
        assert match_rule(text) == EDUCATION, text.splitlines()[1]


def test_regel_schweigt_beim_mehrdeutigen_abschlusszeugnis():
    # Ein Schulzeugnis, dessen einziges Signal "Abschlusszeugnis" ist, geht
    # bewusst ans LLM: dasselbe Wort steht in Aufhebungsverträgen. Der
    # Klassifikations-Prompt trennt beides über die Frage, WAS bescheinigt
    # wird — die Regel kann das nicht.
    text = (
        "Musterschule der Stadt Musterstadt\n"
        "Abschlusszeugnis\n"
        "Frau Muster hat die Schule mit Erfolg besucht.\n"
    )

    assert match_rule(text) is None


def test_regel_erkennt_eine_teilnahmebescheinigung():
    text = (
        "Musterakademie GmbH\n"
        "Teilnahmebescheinigung\n"
        "über den Lehrgang Projektmanagement, 40 Unterrichtsstunden\n"
    )

    assert match_rule(text) == EDUCATION


def test_gehaltsabrechnung_einer_hochschule_bleibt_arbeit():
    # Gegenprobe zur häufigsten Verwechslung: die Bildungseinrichtung ist
    # hier Arbeitgeber, nicht Aussteller eines Nachweises.
    text = (
        "Universität Musterstadt\n"
        "Gehaltsabrechnung für den Monat Mai\n"
        "Bruttolohn 1.234,00 EUR\n"
        "Rentenversicherung AN-Anteil 100,00 EUR\n"
    )

    assert match_rule(text) == EMPLOYMENT


def test_kuendigung_mit_zeugniszusage_entscheidet_die_regel_nicht():
    # "Abschlusszeugnis" ist arbeitsrechtlich ein stehender Begriff. Am
    # Bestand gemessen zog das Wort mit vollem Gewicht Aufhebungsverträge
    # nach education. Die Regel muss hier schweigen und das LLM entscheiden
    # lassen — lieber keine Regel als eine falsche.
    text = (
        "Musterfirma GmbH\n"
        "Aufhebungsvertrag\n"
        "Das Arbeitsverhältnis endet zum 31.12. Der Arbeitgeber erteilt ein "
        "wohlwollendes qualifiziertes Abschlusszeugnis.\n"
        "Der Urlaubsanspruch ist abgegolten.\n"
    )

    assert match_rule(text) != EDUCATION


def test_arbeitszeugnis_bleibt_arbeit():
    text = (
        "Musterfirma GmbH\n"
        "Arbeitszeugnis\n"
        "Herr Muster war vom 01.01. bis 31.12. in unserem Unternehmen tätig.\n"
        "Er erfüllte die ihm übertragenen Aufgaben stets zu unserer vollsten "
        "Zufriedenheit.\n"
    )

    assert match_rule(text) == EMPLOYMENT

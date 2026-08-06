"""Datumsnormalisierung für Dateiname und Archivjahr.

Anlass (Bestandsbefund): Dokumente mit zweistelligem Jahr ("20.06.18") oder
ausgeschriebenem Monat ("20. April 2017") liefen an `normalize_date` vorbei.
Folge war doppelt: der Rohwert landete im Dateinamen UND `extract_year` fand
kein Jahr, sodass das Dokument im Ordner des Importjahres statt des
Dokumentjahres archiviert wurde.

Alle Werte erfunden.
"""

from src.organizer.date_utils import extract_year, normalize_date, to_german_date


def test_deutsches_vollformat_bleibt_wie_bisher():
    assert normalize_date("11.03.2024") == "2024-03-11"


def test_zweistelliges_jahr_wird_verstanden():
    assert normalize_date("20.06.18") == "2018-06-20"
    assert normalize_date("01.01.99") == "1999-01-01"


def test_ausgeschriebener_monat_wird_verstanden():
    assert normalize_date("20. April 2017") == "2017-04-20"
    assert normalize_date("1. Januar 2017") == "2017-01-01"
    assert normalize_date("3. Dezember 2020") == "2020-12-03"


def test_monatsname_ohne_punkt_und_mit_abkuerzung():
    assert normalize_date("20 April 2017") == "2017-04-20"
    assert normalize_date("20. Apr. 2017") == "2017-04-20"
    assert normalize_date("5. Mrz. 2021") == "2021-03-05"


def test_iso_datum_bleibt_unveraendert():
    # Bereits normalisierte Werte dürfen sich beim zweiten Durchlauf nicht
    # ändern (der Dateiname-Bau läuft mehrfach über dieselben Daten).
    assert normalize_date("2024-03-11") == "2024-03-11"


def test_schraegstrich_format_bleibt_bewusst_unangetastet():
    # "01/03/2024" ist zwischen deutschem und US-Format mehrdeutig. Ein
    # still falsch geratenes Datum wäre schlimmer als ein unschöner
    # Dateiname — die Pfadsicherheit übernimmt _safe_filename.
    assert normalize_date("01/03/2024") == "01/03/2024"


def test_unparsbares_bleibt_roh():
    assert normalize_date("Rechnungsdatum unbekannt") == "Rechnungsdatum unbekannt"
    assert normalize_date("") == ""


def test_nicht_string_werte_stuerzen_nicht_ab():
    assert normalize_date(None) is None
    assert normalize_date(2024) == 2024


def test_kein_monatsname_wird_zufaellig_getroffen():
    # "Mai" steckt in "Mailand" — die Erkennung darf nicht auf Teilwörtern
    # anschlagen.
    assert normalize_date("20. Mailand 2017") == "20. Mailand 2017"


def test_to_german_date_wandelt_iso_ins_anzeigeformat():
    # Datumsfelder werden in der App deutsch geführt; ISO ist die interne
    # Form für Dateinamen (normalize_date).
    assert to_german_date("2019-05-23") == "23.05.2019"
    assert to_german_date("2024-03-11") == "11.03.2024"


def test_to_german_date_laesst_deutsches_format_stehen():
    assert to_german_date("23.05.2019") == "23.05.2019"


def test_to_german_date_versteht_dieselben_schreibweisen_wie_normalize():
    assert to_german_date("20. April 2017") == "20.04.2017"
    assert to_german_date("20.06.18") == "20.06.2018"
    assert to_german_date(" 2019-05-23 ") == "23.05.2019"


def test_to_german_date_laesst_unparsbares_und_nicht_strings_unveraendert():
    assert to_german_date("Kontoauszug Nr. 4") == "Kontoauszug Nr. 4"
    assert to_german_date("01/03/2024") == "01/03/2024"
    assert to_german_date("") == ""
    assert to_german_date(None) is None


def test_extract_year_findet_zweistelliges_jahr():
    # Vorher fand die Jahres-Regex in "20.06.18" nichts und das Dokument
    # landete im Ordner des Importjahres.
    assert extract_year({"document_date": "20.06.18"}, fallback_year="2026") == "2018"


def test_extract_year_findet_ausgeschriebenen_monat():
    assert (
        extract_year({"document_date": "20. April 2017"}, fallback_year="2026")
        == "2017"
    )


def test_extract_year_behaelt_vorrang_von_tax_year():
    assert (
        extract_year(
            {"tax_year": "2019", "document_date": "20.06.18"}, fallback_year="2026"
        )
        == "2019"
    )


def test_extract_year_faellt_ohne_datum_zurueck():
    assert extract_year({}, fallback_year="2026") == "2026"
    assert extract_year({"document_date": "unbekannt"}, fallback_year="2026") == "2026"

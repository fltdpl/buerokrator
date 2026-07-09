"""Regelparser für Jahreskontoauszüge und Steuerbescheinigungen.

Die Textausschnitte stammen aus echten OCR-Ergebnissen der Ground Truth und
decken die zwei Layouts ab, die Tesseract liefert: Beschriftung und Betrag
nebeneinander, oder spaltenweise getrennte Blöcke.
"""

from src.extraction.account_statement import parse_account_statement
from src.extraction.pension_refiner import refine_pension_fields
from src.extraction.tax_certificate import parse_tax_certificate

# Layout A: Beschriftung, Wertstellung und Betrag stehen auf einer Zeile.
INLINE_STATEMENT = """
Debeka
Bausparkasse AG

Jahreskontoauszug 2025 - Bausparkonto - Tarif BS4

Buchungstext (Erläuterungen siehe Rückseite) Wertstellung Umsatz EUR
Saldovortrag 12.345,67 +
Lastschrifteinzug 31.01.2025 300,00 +
Lastschrifteinzug 28.02.2025 300,00 +
Guthabenzinsen 31.12.2025 55,55 +
Kapitalertragsteuer 31.12.2025 13,88 -
Solidaritätszuschlag 31.12.2025 0,76 -
Endsaldo

15.986,58 +

Bausparnummer: 555000123
Bausparsumme: 100.000 EUR
Freistellungsbetrag bis
31.12.2025: 0,00 EUR
"""

# Layout B: Beschriftungen, Daten und Beträge in getrennten Blöcken —
# und OCR hat vier der zwölf Lastschriftzeilen verloren.
COLUMN_STATEMENT = """
Debeka
Bausparkasse AG

Jahreskontoauszug 2023 - Bausparkonto - Tarif BS4

Buchungstext (Erläuterungen siehe Rückseite)

Saldovortrag
Lastschrifteinzug
Guthabenzinsen
Kapitalertragsteuer
Solidaritätszuschlag
Endsaldo

31.01.2023
31.12.2023

8.111,11 +
300,00 +
300,00 +
300,00 +
300,00 +
300,00 +
300,00 +
300,00 +
300,00 +
44,44 +
11,11 -
0,61 -
11.743,83 +

Bausparnummer: 555000123
Bausparsumme: 100.000 EUR
"""

TAX_CERTIFICATE = """
Debeka
Bausparkasse AG - Ihr Baufinanzierer

Steuerbescheinigung 2019
Bescheinigung für alle Privatkonten und / oder -depots

Höhe der Kapitalerträge EUR 21,12
Zeile 7 Anlage KAP

Höhe des in Anspruch genommenen
Sparer-Pauschbetrages EUR 0,00
Zeile 12 oder 13 Anlage KAP

Kapitalertragsteuer EUR 5,03
Zeile 48 Anlage KAP

Solidaritätszuschlag EUR 0,19
Zeile 49 Anlage KAP

Kirchensteuer zur Kapitalertragsteuer EUR 0,00
Zeile 50 Anlage KAP
"""


def test_inline_statement_liest_salden_und_zinsen():
    fields = parse_account_statement(INLINE_STATEMENT)

    assert fields["opening_balance"] == 12345.67
    assert fields["closing_balance"] == 15986.58
    assert fields["interest"] == 55.55
    assert fields["document_subtype"] == "bauspar_jahresauszug"
    assert fields["policy_number"] == "555000123"


def test_beitragssumme_wird_aus_der_bilanz_abgeleitet():
    # 15.986,58 - 12.345,67 - 55,55 + 13,88 + 0,76 = 3600,00 — obwohl im Text
    # nur zwei der zwölf Lastschriften stehen.
    assert parse_account_statement(INLINE_STATEMENT)["contributions_total"] == 3600.0


def test_spalten_layout_mit_fehlenden_lastschriftzeilen():
    fields = parse_account_statement(COLUMN_STATEMENT)

    assert fields["opening_balance"] == 8111.11
    assert fields["closing_balance"] == 11743.83
    assert fields["interest"] == 44.44
    assert fields["contributions_total"] == 3600.0


def test_bausparsumme_wird_nicht_als_saldo_gelesen():
    # "100.000 EUR" trägt kein Vorzeichen und gehört nicht zur Buchungstabelle.
    for text in (INLINE_STATEMENT, COLUMN_STATEMENT):
        assert parse_account_statement(text)["opening_balance"] != 100000.0


def test_parser_raet_weder_aussteller_noch_produkt_noch_datum():
    # Diese Felder sind je Anbieter verschieden. Ein Layout-Treffer darf sie
    # NICHT setzen, sonst bekäme ein Schwäbisch-Hall-Auszug den Aussteller
    # des Anbieters, für den das Muster einmal geschrieben wurde.
    fields = parse_account_statement(INLINE_STATEMENT)

    assert "issuer" not in fields
    assert "product_name" not in fields
    assert "document_date" not in fields


def test_fremder_anbieter_behaelt_seinen_aussteller():
    foreign = INLINE_STATEMENT.replace("Debeka\nBausparkasse AG", "Schwäbisch Hall AG")
    llm = {"issuer": "Schwäbisch Hall AG", "product_name": "Bausparvertrag"}

    refined = refine_pension_fields(foreign, llm)

    assert refined["issuer"] == "Schwäbisch Hall AG"
    assert refined["contributions_total"] == 3600.0


def test_parser_schweigt_wenn_die_betragsspalte_fehlt():
    # OCR-Ausfall: nur der Endsaldo ist lesbar — dann lieber nichts liefern
    # als raten.
    broken = """
    Kontoauszug 2022 - Bausparkonto - Tarif BS4
    Saldovortrag
    Lastschrifteinzug 31.01.2022
    Guthabenzinsen 31.12.2022
    Kapitalertragsteuer
    Solidaritätszuschlag
    Endsaldo
    8.111,11 +
    """

    assert parse_account_statement(broken) == {}


def test_unbekanntes_layout_wird_nicht_angefasst():
    # Ein Girokonto-Auszug hat Saldovortrag und Endsaldo, aber kein Layout.
    girokonto = INLINE_STATEMENT.replace("Bausparkonto", "Girokonto")

    assert parse_account_statement(girokonto) == {}


def test_fremdes_dokument_wird_nicht_angefasst():
    assert parse_account_statement("Rechnung über 42,00 EUR") == {}
    assert parse_tax_certificate("Rechnung über 42,00 EUR") == {}


def test_steuerbescheinigung_ordnet_betraege_zeilenrichtig_zu():
    fields = parse_tax_certificate(TAX_CERTIFICATE)

    assert fields["interest"] == 21.12
    assert fields["capital_gains_tax"] == 5.03
    assert fields["soli"] == 0.19
    assert fields["church_tax"] == 0.0


def test_steuerbescheinigung_ist_anbieterunabhaengig():
    # Amtliches Formular (§ 45a EStG): gleiche Beschriftungen bei jeder Bank.
    broker = TAX_CERTIFICATE.replace("Debeka\nBausparkasse AG", "Beispielbank eG")

    assert parse_tax_certificate(broker)["interest"] == 21.12
    assert "issuer" not in parse_tax_certificate(broker)


def test_refine_korrigiert_verrutschte_llm_werte():
    # Das LLM liest die Betragsspalte um eine Zeile versetzt.
    llm = {
        "document_subtype": "steuerbescheinigung",
        "issuer": "Debeka",
        "interest": 5.03,
        "capital_gains_tax": 0.19,
        "soli": 0.0,
    }

    refined = refine_pension_fields(TAX_CERTIFICATE, llm)

    assert refined["interest"] == 21.12
    assert refined["capital_gains_tax"] == 5.03
    assert refined["soli"] == 0.19
    assert refined["issuer"] == "Debeka"


def test_refine_laesst_unbekannte_dokumente_unveraendert():
    llm = {"issuer": "VBL", "amount": 111.04}

    assert refine_pension_fields("Renteninformation der VBL", llm) == llm

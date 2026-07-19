"""Regelparser für Entgeltnachweise (SAP-HR-Layout).

Fixture bildet das stark zerrissene Layout nach — alle Zahlen erfunden.
"""

from src.extraction.entgeltnachweis import (
    is_entgeltnachweis,
    parse_entgeltnachweis,
)

FIXTURE = "\n".join(
    [
        "Lfd  . Nr  .  123",
        "Muster AG HR Postfach 11 22 12345 Musterstadt",
        "VERTRAULICH",
        "Entgeltnachwei s für  Februar 2024  Lfd  . Nr  . :  123  Seite :  1",
        "LArt ENTGELTBESTANDTEILE  Kennz  Betrag  Zr  Summe",
        "0B12 Monat sentgelt  LSG  77 ,00 S  2  .345 ,67",
        "Gesamtbrutto ( EBV) :  2  .460 ,89",
        "GESETZLICHE ABZÜGE",
        "Y$32 Lohnsteuer , lfd  .  210 ,55",
        "/ 55E Geset zl  . Netto ( EBV)  1  .765 ,43",
        "JAHRESSUMMEN",
        "G  t B  t :  4 921 78",
    ]
)


def test_detects_entgeltnachweis():
    assert is_entgeltnachweis(FIXTURE)
    assert not is_entgeltnachweis("Rechnung Nr. 42")


def test_parses_period_and_amounts():
    fields = parse_entgeltnachweis(FIXTURE)

    assert fields["document_subtype"] == "gehaltsabrechnung"
    assert fields["tax_year"] == "2024"
    # Abrechnungsmonat aus dem Titel (inkl. Schaltjahr-Monatsende).
    assert fields["period_start"] == "01.02.2024"
    assert fields["period_end"] == "29.02.2024"
    assert fields["gross_amount"] == 2460.89
    assert fields["net_amount"] == 1765.43
    # Nichts Identifizierendes aus Regeln.
    assert "employer" not in fields


def test_missing_net_leaves_field_unset():
    without_net = "\n".join(
        line for line in FIXTURE.splitlines() if "Netto" not in line
    )

    fields = parse_entgeltnachweis(without_net)

    assert fields["gross_amount"] == 2460.89
    assert "net_amount" not in fields


def test_unknown_layout_returns_empty():
    assert parse_entgeltnachweis("Gehaltsabrechnung ohne Anker") == {}

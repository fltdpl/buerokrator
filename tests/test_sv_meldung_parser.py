"""Regelparser für die SV-Meldebescheinigung (§ 25 DEÜV).

Fixture bildet das rekonstruierte Layout nach (zerrissene Wörter, Encoding-
Artefakte wie „DEèV"). Alle Nummern/Zahlen sind erfunden.
"""

from src.extraction.sv_meldung import is_sv_meldung, parse_sv_meldung

FIXTURE = "\n".join(
    [
        "MUSTER GMBH  Personal nummer  777001  .0",
        "Besche i n igung  - Soz i al vers i cherung",
        "nach ü 25 DEèV vom 10 . Febr  .1998",
        "Vers i cher ungsnummer  99999999X999",
        "Art der Mel dung  -  Jahresmel dung",
        "Von  bi s  Entgel t  Gr und der Abgabe",
        "01  .01  .2023  31  .12  .2023  004321 EURO  50  - Jahresentgel t",
        "Bet r i ebsnummer  Name der E i nzugsst el l e",
        "11111111  MUSTERKASSE",
    ]
)


def test_detects_sv_meldung():
    assert is_sv_meldung(FIXTURE)
    assert not is_sv_meldung("Gehaltsabrechnung Januar 2023")


def test_parses_meldegrund_and_zeitraum():
    fields = parse_sv_meldung(FIXTURE)

    assert fields["document_subtype"] == "sv_meldung"
    assert fields["subject"] == "Jahresmeldung"
    # Zeitraum aus der Entgelt-Tabellenzeile, nicht aus beliebigen Daten.
    assert fields["period_start"] == "01.01.2023"
    assert fields["period_end"] == "31.12.2023"
    # Nichts Identifizierendes aus Regeln.
    assert "issuer" not in fields


def test_stornierung_wins_over_original_meldung():
    text = FIXTURE.replace(
        "Art der Mel dung  -  Jahresmel dung",
        "Art der Mel dung  -  Stor n i er ung ei ner Jahresmel dung",
    )

    assert parse_sv_meldung(text)["subject"] == "Stornierung"


def test_unknown_meldegrund_is_left_to_llm():
    text = FIXTURE.replace(
        "Art der Mel dung  -  Jahresmel dung",
        "Art der Mel dung  -  GVX-Sondervorgang 77",
    )

    assert "subject" not in parse_sv_meldung(text)


def test_unknown_layout_returns_empty():
    assert parse_sv_meldung("Rechnung Nr. 42") == {}


def test_storno_plus_neuausstellung_uses_final_meldung():
    # Ein PDF mit Stornierung (Seite 1) und korrigierter Jahresmeldung
    # (Seite 2): der finale Stand zählt, inkl. Zeitraum der Neuausstellung.
    text = "\n".join(
        [
            "Besche i n igung  - Soz i al vers i cherung",
            "Art der Mel dung  -  Jahresmel dung  Stor ni er ung",
            "Von  bi s  Entgel t",
            "01  .01  .2022  30  .06  .2022  001111 EURO  50",
            "Besche i n igung  - Soz i al vers i cherung",
            "Art der Mel dung  -  Jahresmel dung",
            "Von  bi s  Entgel t",
            "01  .01  .2022  31  .12  .2022  002222 EURO  50",
        ]
    )

    fields = parse_sv_meldung(text)

    assert fields["subject"] == "Jahresmeldung"
    assert fields["period_start"] == "01.01.2022"
    assert fields["period_end"] == "31.12.2022"

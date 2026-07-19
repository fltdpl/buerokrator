"""Regelparser für den amtlichen LStB-Ausdruck.

Das Fixture bildet das rekonstruierte Layout nach (zerrissene Wörter,
Ziffern-Lücken, halbzeilig versetzte Werte) — alle Zahlen sind erfunden.
"""

from src.extraction.lohnsteuerbescheinigung import (
    is_lohnsteuerbescheinigung,
    parse_lohnsteuerbescheinigung,
)

FIXTURE = "\n".join(
    [
        "1 47200 - >04100< - JANUAR 2025",
        "MUSTER GMBH  Personal n u m mer  777001 . 0",
        "Ausdruck der elektronischen Lohnsteuerbescheinigung fÞr 2024",
        "Nachstehende Daten wu rden masch i nell Þ bertragen.",
        "vom - bis",
        "MUSTER GMBH  B  1 . Beschei nigu ngszeitrau m  01  .02  .  -31  .12  .",
        "TESTWEG . 9 12345 MUSTERSTADT 3",
        "EUR Ct",
        "HERRN  3 . Bruttoarbeitsloh n ei nschl . SachbezÞge  4 32 1 09",
        "ohne 9. und 1 0.",
        "4 . Ei nbeh altene Loh nsteuer",
        "MAX MUSTER  von 3  1 .  023 45",
        "5 . Ei nbehaltener Solidaritåtszuschl ag",
        "von 3  67 8 9",
        "6 . Ei nbehaltene Ki rchensteuer des Arbeitnehmers",
        "von 3  - - - - - -",
        "1 1 . Ei nbehaltene Lohnsteuer",
        "von 9. und 1 0.",
        "1 2 . Ei nbehaltener Solidaritåtszuschl ag",
        "Steuerfreier Jah resbetrag  22 . Arbeitgeber  Rentenversicheru ng  4 56 78",
        "Jah resh i nzu rech n u ngsbetrag  23 . Arbeitneh mer  Rentenversicheru ng  4 56 78",
        "25 . Arbeitneh merbeitråge zu r gesetzl ichen  3 21 09",
        "Krankenversicheru ng",
        "26 . Arbeitneh merbeitråge zu r sozi alen Pflegeversicheru ng  87 65",
        "54 32",
        "27 . Arbeitneh merbeitråge zu r Arbeitslosenversicheru ng",
        "28 . Beitråge zu r privaten Kranken - u . Pflege",
        "Pfl ichtversicheru ng oder M i ndestvorsorgepauschale",
        "AKDB- Form 0 1 5/60 1 /72 1 - 1 0.20 1 9",
    ]
)


def test_detects_official_printout():
    assert is_lohnsteuerbescheinigung(FIXTURE)
    assert not is_lohnsteuerbescheinigung("Gehaltsabrechnung Januar 2024")


def test_parses_all_labeled_lines():
    fields = parse_lohnsteuerbescheinigung(FIXTURE)

    assert fields["document_subtype"] == "lohnsteuerbescheinigung"
    assert fields["tax_year"] == "2024"
    # Zeitraum: Tage/Monate aus der Formularzeile, Jahr aus dem Titel.
    assert fields["period_start"] == "01.02.2024"
    assert fields["period_end"] == "31.12.2024"

    # Werte trotz zerrissener Ziffern (letzte zwei Ziffern = Cent).
    assert fields["gross_amount"] == 4321.09
    # Wert auf der Nachbarzeile, Wertespalte in mehreren Segmenten.
    assert fields["income_tax"] == 1023.45
    assert fields["soli"] == 67.89
    # Leermarkierung („- - -") = bescheinigte 0.
    assert fields["church_tax"] == 0.0
    assert fields["pension_insurance_employer"] == 456.78
    assert fields["pension_insurance_employee"] == 456.78
    assert fields["health_insurance"] == 321.09
    assert fields["care_insurance"] == 87.65
    # Halbzeilig versetzter Wert ZWISCHEN den Labels 26 und 27.
    assert fields["unemployment_insurance"] == 54.32
    # Leeres SV-Feld = kein Beitrag bescheinigt.
    assert fields["private_health_insurance"] == 0.0


def test_line_11_does_not_shadow_line_4():
    # „11. Einbehaltene Lohnsteuer" (ermäßigt besteuerte Bezüge) darf den
    # Wert von Zeile 4 nicht überschreiben oder liefern.
    without_4 = "\n".join(
        line
        for line in FIXTURE.splitlines()
        if "4 . Ei nbeh altene" not in line and "MAX MUSTER" not in line
    )

    fields = parse_lohnsteuerbescheinigung(without_4)

    assert "income_tax" not in fields


def test_unknown_layout_returns_empty():
    assert parse_lohnsteuerbescheinigung("Rechnung Nr. 42 Betrag 12,34") == {}


def test_blank_tax_lines_are_not_zeroed():
    # Fehlt der Wert einer Steuerzeile (3.-6.), wird NICHT still 0 gesetzt —
    # nur der SV-Block (22.-28.) hat Leerfeld-Semantik „kein Beitrag".
    minimal = "\n".join(
        [
            "Ausdruck der elektronischen Lohnsteuerbescheinigung fÞr 2024",
            "4 . Ei nbeh altene Loh nsteuer",
            "von 3",
        ]
    )

    fields = parse_lohnsteuerbescheinigung(minimal)

    assert "income_tax" not in fields


def test_fallbacks_for_scrambled_micro_labels():
    # Die zweizeiligen Mikroschrift-Labels (22./23./28.) zerfallen bei
    # manchen Ausdrucken; Zeitraum-Punkte können verloren gehen. Die
    # Fallback-Anker (Rentenversicherungs-Wertzeilen, „Mindestvorsorge-
    # pauschale") müssen trotzdem lesen. Alle Zahlen erfunden.
    scrambled = "\n".join(
        [
            "Ausdruck der elektronischen Lohnsteuerbescheinigung fÞr 2023",
            "MUSTER GMBH  B  1 . Beschei nigu ngszeitrau m  01 03  -31 12",
            "HERRN  3 . Bruttoarbeitsloh n ei nschl . SachbezÞge  5 43 2 10",
            "Steuerfreier Jah resbetrag  .  rbe tgeber  Rentenversicheru ng  5 05 05",
            "Jah reshi nzu rech n u n sbetra  2  A  i  h",
            "g  g  3 .  rbe tne mer  Rentenversicheru ng  5 05 05",
            "2  B i  i  K  k",
            "8 .  e tråge zu r pr vaten  ran en  u .  ege",
            "Pflichtversicheru ng oder Mi ndestvorsorgepausch ale",
        ]
    )

    fields = parse_lohnsteuerbescheinigung(scrambled)

    assert fields["period_start"] == "01.03.2023"
    assert fields["period_end"] == "31.12.2023"
    assert fields["gross_amount"] == 5432.10
    assert fields["pension_insurance_employer"] == 505.05
    assert fields["pension_insurance_employee"] == 505.05
    # Leeres Feld hinter dem 28er-Anker = kein Beitrag bescheinigt.
    assert fields["private_health_insurance"] == 0.0


def test_pension_fallback_single_value_fills_both_sides():
    # Nur eine Rentenversicherungs-Wertzeile rekonstruierbar: die Beiträge
    # sind paritätisch, beide Seiten tragen denselben bescheinigten Wert.
    text = "\n".join(
        [
            "Ausdruck der elektronischen Lohnsteuerbescheinigung fÞr 2023",
            "irgendwas  Rentenversicheru ng  6 07 08",
        ]
    )

    fields = parse_lohnsteuerbescheinigung(text)

    assert fields["pension_insurance_employer"] == 607.08
    assert fields["pension_insurance_employee"] == 607.08

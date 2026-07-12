from src.core.document_types import (
    BANK,
    EMPLOYMENT,
    HOUSING,
    INSURANCE,
    INVOICE,
    PENSION,
    TAX,
)

# Gewichtete Schlüsselwörter je Dokumenttyp. Statt "erste Regel gewinnt"
# werden alle Treffer gezählt (Scoring): das verhindert, dass ein beiläufig
# erwähntes Wort (z. B. "Einkommensteuererklärung" im Kleingedruckten eines
# Bauspar-Auszugs) das eigentliche Dokumentthema übertrumpft.
#
# Gewichte: 3 = eindeutige Dokumenttitel, 2 = starke Indizien, 1 = schwache
# Hinweise. Treffer im ersten Textdrittel zählen doppelt (Titel stehen oben).
KEYWORD_WEIGHTS = {
    TAX: (
        # Nur noch Finanzamt-/Sozialversicherungs-Dokumente: die Lohn- und
        # Gehaltsdokumente vom Arbeitgeber sind nach employment gewandert.
        ("einkommensbescheinigung", 3),
        ("meldebescheinigung", 3),
        ("einkommensteuerbescheid", 3),
        # bewusst schwach: taucht als Nebensatz in vielen Dokumenten auf
        # ("für Ihre Einkommensteuererklärung ...")
        ("einkommensteuer", 1),
        ("finanzamt", 1),
    ),
    EMPLOYMENT: (
        ("lohnsteuerbescheinigung", 3),
        ("gehaltsabrechnung", 3),
        ("entgeltabrechnung", 3),
        ("lohnabrechnung", 3),
        ("verdienstbescheinigung", 3),
        ("bezügemitteilung", 3),
        ("bezuegemitteilung", 3),
        ("arbeitsvertrag", 3),
        ("arbeitszeugnis", 3),
        ("zwischenzeugnis", 3),
        # bewusst schwach: "Kündigung" kommt auch bei Versicherungen/Verträgen
        # vor; "arbeitgeber" ist nur ein Indiz.
        ("kündigung", 1),
        ("kuendigung", 1),
        ("arbeitgeber", 1),
    ),
    PENSION: (
        # kein bloßes "bauspar": die Debeka-Tagline "Versichern · Bausparen"
        # steht auf JEDEM Debeka-Dokument, auch Versicherungen
        ("bausparvertrag", 3),
        ("bausparkasse", 3),
        ("für ihre rentenversicherung", 3),
        ("renteninformation", 3),
        ("betriebsrente", 3),
        ("riester", 3),
        # bewusst schwach: stehen als Beitragszeilen auf jeder
        # Gehaltsabrechnung und dürfen dort nicht dominieren.
        # "vbl" fehlt absichtlich (VBL-Umlage auf Abrechnungen im
        # öffentlichen Dienst) — VBL-Dokumente entscheidet das LLM.
        ("rentenversicherung", 1),
        ("altersvorsorge", 1),
        # auch in Bedingungen von Lebensversicherungen (Zusatzversicherung)
        ("berufsunfähigkeit", 1),
    ),
    INSURANCE: (
        ("versicherungsschein", 3),
        ("für ihre lebensversicherung", 3),
        # bewusst schwach: auch Rentenversicherungen haben BU-Zusätze
        ("zusatzversicherung", 1),
        ("versicherungsbestätigung", 3),
        ("versicherungsbestaetigung", 3),
        ("unfallversicherung", 2),
        ("haftpflichtversicherung", 2),
        ("hausratversicherung", 2),
        ("rechtsschutzversicherung", 2),
        ("beitragsrechnung", 2),
        # bewusst schwach: Beitragszeile auf Gehaltsabrechnungen
        ("krankenversicherung", 1),
    ),
    INVOICE: (
        ("rechnungsnummer", 2),
        ("rechnungsbetrag", 2),
        ("zahnarzt", 2),
    ),
    BANK: (
        # bewusst schwach: Bauspar-Jahresauszüge heißen "Jahreskontoauszug" —
        # dort entscheidet "bausparkasse"/"bauspar" mit höherem Gewicht.
        ("kontoauszug", 2),
    ),
    HOUSING: (
        ("nebenkostenabrechnung", 3),
        ("betriebskostenabrechnung", 3),
        ("mietvertrag", 3),
    ),
}

# Regel greift nur bei klarem Ergebnis: Mindest-Score UND Vorsprung vor dem
# Zweitplatzierten. Alles andere entscheidet das LLM.
MIN_SCORE = 3
MIN_MARGIN = 2


def _score_details(text):
    lowered = text.lower()
    head = lowered[: max(len(lowered) // 3, 200)]

    scores = {}
    max_weights = {}
    for document_type, keywords in KEYWORD_WEIGHTS.items():
        score = 0
        max_weight = 0
        for keyword, weight in keywords:
            if keyword in head:
                score += weight * 2
            elif keyword in lowered:
                score += weight
            else:
                continue
            max_weight = max(max_weight, weight)
        scores[document_type] = score
        max_weights[document_type] = max_weight

    return scores, max_weights


def score_types(text):
    """Berechnet den Keyword-Score je Dokumenttyp.

    Jedes Schlüsselwort zählt einmal (Präsenz, nicht Häufigkeit); steht es im
    ersten Textdrittel, zählt es doppelt.
    """
    return _score_details(text)[0]


def match_rule(text):
    """Gibt den Dokumenttyp zurück, wenn das Scoring eindeutig ist, sonst None.

    Neben Mindest-Score und Vorsprung muss mindestens ein Treffer mit
    Gewicht >= 2 dabei sein: eine Ansammlung schwacher Hinweiswörter
    (z. B. Beitragszeilen) allein darf keine Regel-Entscheidung auslösen.
    """
    scores, max_weights = _score_details(text)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    best_type, best_score = ranked[0]
    second_score = ranked[1][1]

    if (
        best_score >= MIN_SCORE
        and best_score - second_score >= MIN_MARGIN
        and max_weights[best_type] >= 2
    ):
        return best_type

    return None

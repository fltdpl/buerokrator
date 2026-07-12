from src.classifier.rule_classifier import match_rule, score_types


def test_bauspar_beats_einkommensteuer_mention():
    # Bauspar-Jahresauszüge erwähnen die Einkommensteuererklärung im
    # Kleingedruckten — das darf den Bauspar-Titel nicht übertrumpfen.
    text = (
        "Debeka Bausparkasse AG — Jahresauszug zu Ihrem Bausparvertrag 555000123\n"
        + "Kontostand, Zinsen, Guthaben...\n" * 30
        + "Diese Bescheinigung dient für Ihre Einkommensteuererklärung."
    )
    assert match_rule(text) == "pension"


def test_payslip_with_contribution_lines_stays_employment():
    # Gehaltsabrechnungen listen Renten-/Kranken-/Arbeitslosenversicherung
    # und betriebliche Altersvorsorge als Beitragszeilen auf — sie sind aber
    # Arbeitgeber-Dokumente (employment), nicht insurance.
    text = (
        "Gehaltsabrechnung März 2024\n"
        "Rentenversicherung 450,00\n"
        "Krankenversicherung 320,00\n"
        "Betriebliche Altersvorsorge 100,00\n"
        "VBL-Umlage 50,00\n"
    )
    assert match_rule(text) == "employment"


def test_generic_versicherung_alone_is_not_insurance():
    # "Versicherung" als bloßes Wort (z. B. "Sozialversicherung") reicht
    # nicht mehr für insurance.
    assert match_rule("Ein Hinweis auf die Sozialversicherung ohne weitere Merkmale") is None


def test_insurance_title_documents_match():
    assert match_rule("Versicherungsschein zur Hausratversicherung") == "insurance"


def test_ambiguous_text_falls_back_to_llm():
    # Zwei starke Titel unterschiedlicher Typen: kein klarer Vorsprung.
    text = "Lohnsteuerbescheinigung und Versicherungsschein"
    assert match_rule(text) is None


def test_bauspar_jahreskontoauszug_is_pension_not_bank():
    # Bauspar-Jahresauszüge heißen im Dokument "Jahreskontoauszug" — der
    # Absender "Bausparkasse" muss den Kontoauszug-Treffer überstimmen.
    text = "Debeka Bausparkasse AG\nJahreskontoauszug 2022\nGuthaben..."
    assert match_rule(text) == "pension"


def test_plain_kontoauszug_is_bank():
    assert match_rule("Kontoauszug Nr. 7 — Girokonto") == "bank"


def test_weak_words_alone_never_decide():
    # Nur schwache Hinweiswörter (Gewicht 1), auch gehäuft im Kopf:
    # keine Regel-Entscheidung, das LLM soll entscheiden.
    text = "Rentenversicherung Altersvorsorge Berufsunfähigkeit"
    assert match_rule(text) is None


def test_head_hits_count_double():
    text = "Bausparvertrag\n" + "Fülltext ohne Schlüsselwörter " * 100
    scores = score_types(text)
    # 3er-Keyword im ersten Drittel zählt doppelt
    assert scores["pension"] == 6


def test_rentenversicherung_policy_beats_versicherungsschein():
    # Rentenversicherungs-Policen tragen den Titel "für Ihre Renten-
    # versicherung", enthalten aber auch "Versicherungsschein" → pension.
    text = (
        "für Ihre Rentenversicherung Service-Nr. 123\n"
        "Wir stellen diesen Versicherungsschein aus."
    )
    assert match_rule(text) == "pension"


def test_lebensversicherung_policy_is_insurance():
    text = (
        "Nachtrag zum Versicherungsschein\n"
        "für Ihre Lebensversicherung Ausfertigungs-Nr. 007"
    )
    assert match_rule(text) == "insurance"

"""Kategorie Gesundheit (health): Vokabular, Felder, Abgrenzung.

Zwei Grenzen sind hier der eigentliche Prüfstein, und beide sind teuer, wenn
sie brechen:

1. **Arztrechnungen bleiben `invoice`** — daran hängt der Steuerzweck
   `krankheitskosten`.
2. **Beiträge zur Kranken-/Pflegeversicherung bleiben `insurance`** — die
   Vorsorge-Auswertung erkennt sie an den Zeichenketten "kranken"/"pflege"
   (`src/tax/tax_summary.py`). Zöge das Wort "Krankenkasse" Dokumente
   hierher, fielen Vorsorgeaufwendungen still aus der Erklärung.

Deshalb steht neben jedem Positivfall eine Gegenprobe. Alle Namen, Beträge
und Nummern sind erfunden.
"""

from pathlib import Path

import yaml

from src.classifier.document_extractor import PROMPT_FILES
from src.classifier.rule_classifier import KEYWORD_WEIGHTS, match_rule
from src.core.document_display import get_document_art_label
from src.core.document_fields import (
    ALLOWED_FIELDS,
    KNOWN_SUBTYPES,
    SUBTYPE_ALIASES,
    constrain_subtype,
    normalize_subtype,
    whitelist_fields,
)
from src.core.document_types import (
    ARCHIVE_CATEGORY_LABELS,
    DOCUMENT_TYPE_LABELS,
    DOCUMENT_TYPES,
    EMPLOYMENT,
    HEALTH,
    INVOICE,
)
from src.organizer.filename_builder import build_filename
from src.services.form_schema import HEALTH_SUBTYPE_LABELS, form_fields
from src.tax.tax_relevance import default_tax_relevance

REPO = Path(__file__).resolve().parents[1]

UNTERARTEN = {
    "arztunterlagen",
    "krankenkasse",
    "reha",
    "attest",
    "impfung",
    "sonstiges",
}


# --- Vokabular und Felder ---------------------------------------------


def test_vokabular_hat_genau_sechs_unterarten():
    assert KNOWN_SUBTYPES[HEALTH] == UNTERARTEN
    assert set(HEALTH_SUBTYPE_LABELS) == UNTERARTEN


def test_typ_ist_ueberall_registriert():
    assert HEALTH in DOCUMENT_TYPES
    assert DOCUMENT_TYPE_LABELS[HEALTH] == "Gesundheit"
    assert ARCHIVE_CATEGORY_LABELS[HEALTH] == "Gesundheit"


def test_settings_kennt_typ_und_archivordner():
    settings = yaml.safe_load((REPO / "config" / "settings.yaml").read_text(encoding="utf-8"))

    assert HEALTH in settings["supported_document_types"]
    assert settings["archive"]["category_mapping"][HEALTH] == "Gesundheit"


def test_whitelist_haelt_die_vier_felder_und_verwirft_den_rest():
    data = {
        "document_subtype": "arztunterlagen",
        "issuer": "Musterpraxis",
        "document_date": "12.03.2026",
        "subject": "Befundbericht",
        "amount": 148.5,
        "policy_number": "PN-1",
    }

    result = whitelist_fields(HEALTH, data)

    assert result == {
        "document_subtype": "arztunterlagen",
        "issuer": "Musterpraxis",
        "document_date": "12.03.2026",
        "subject": "Befundbericht",
    }


def test_kein_betrag_im_feldsatz():
    """Die Kosten stehen auf der Rechnung, nicht auf dem Befund (ADR 014)."""
    assert "amount" not in ALLOWED_FIELDS[HEALTH]


# --- Alias-Tabelle: das Kernstück -------------------------------------


def test_aliase_treffen_reale_wortlaute():
    faelle = {
        "arztbrief": "arztunterlagen",
        "befundbericht": "arztunterlagen",
        "laborbefund": "arztunterlagen",
        "entlassungsbericht": "arztunterlagen",
        "operationsbericht": "arztunterlagen",
        "leistungsbescheid": "krankenkasse",
        "zuzahlungsbefreiung": "krankenkasse",
        "kostenübernahme": "krankenkasse",
        "rehabilitation": "reha",
        "anschlussheilbehandlung": "reha",
        "kur": "reha",
        "arbeitsunfähigkeitsbescheinigung": "attest",
        "krankmeldung": "attest",
        "attest": "attest",
        "impfbescheinigung": "impfung",
        "impfpass": "impfung",
    }

    for wortlaut, erwartet in faelle.items():
        assert normalize_subtype(HEALTH, wortlaut) == erwartet, wortlaut


def test_fuzzy_match_allein_traegt_die_kategorie_nicht():
    """Wie bei education: der Ähnlichkeitsvergleich (cutoff 0,85) erkennt
    keinen der realen Wortlaute. Ohne Alias-Tabelle liefe jedes echte
    Dokument über constrain_subtype in "sonstiges" — die Tabelle ist deshalb
    kein Komfort, sondern trägt die Kategorie."""
    ohne_alias = {
        wortlaut: erwartet
        for wortlaut, erwartet in SUBTYPE_ALIASES[HEALTH].items()
        if wortlaut not in UNTERARTEN
    }

    assert ohne_alias, "Alias-Tabelle ist leer"

    treffer_ohne_tabelle = [
        wortlaut
        for wortlaut in ohne_alias
        if _normalisiert_ohne_aliastabelle(wortlaut) in UNTERARTEN
    ]

    assert treffer_ohne_tabelle == []


def _normalisiert_ohne_aliastabelle(wortlaut):
    from difflib import get_close_matches

    close = get_close_matches(wortlaut, KNOWN_SUBTYPES[HEALTH], n=1, cutoff=0.85)

    return close[0] if close else wortlaut


def test_erfundene_unterart_landet_in_sonstiges_und_rettet_den_wortlaut():
    result = constrain_subtype(
        HEALTH,
        {"document_subtype": "Kleines Blutbild", "issuer": "Musterlabor"},
    )

    assert result["document_subtype"] == "sonstiges"
    assert result["subject"] == "Kleines Blutbild"


def test_vorhandener_betreff_wird_nicht_ueberschrieben():
    result = constrain_subtype(
        HEALTH,
        {"document_subtype": "Kleines Blutbild", "subject": "Kontrolluntersuchung"},
    )

    assert result["subject"] == "Kontrolluntersuchung"


# --- Regel-Klassifikator: Positivfälle --------------------------------


ARZTBRIEF = """
Praxis fuer Innere Medizin Muster
Arztbrief

Sehr geehrte Frau Kollegin,

wir berichten ueber die gemeinsame Patientin, die sich am 12.03.2026 in
unserer Sprechstunde vorstellte.

Anamnese: seit vier Wochen belastungsabhaengige Beschwerden.
Befund: unauffaellig.
Diagnose: Verdacht auf Muskelreizung.
"""

AU_BESCHEINIGUNG = """
Arbeitsunfaehigkeitsbescheinigung
Ausfertigung zur Vorlage beim Arbeitgeber

Musterkasse
arbeitsunfaehig seit 03.02.2026
voraussichtlich arbeitsunfaehig bis 07.02.2026
"""

IMPFBESCHEINIGUNG = """
Impfbescheinigung

Musterpraxis
Impfung gegen Musterkrankheit am 04.05.2026
Chargennummer MU-1234
"""

REHA_BERICHT = """
Musterklinik fuer Rehabilitation
Aerztlicher Entlassungsbericht

Rehabilitationsmassnahme vom 01.04.2026 bis 22.04.2026
Kostentraeger: Deutsche Musterrentenversicherung
"""


def test_regel_erkennt_arztbrief():
    assert match_rule(ARZTBRIEF) == HEALTH


def test_regel_erkennt_arbeitsunfaehigkeitsbescheinigung():
    """Die AU gehoert zu Gesundheit, obwohl "Arbeitgeber" darauf steht."""
    assert match_rule(AU_BESCHEINIGUNG) == HEALTH


def test_regel_erkennt_impfbescheinigung():
    assert match_rule(IMPFBESCHEINIGUNG) == HEALTH


def test_regel_erkennt_reha_entlassungsbericht_trotz_rentenversicherung():
    assert match_rule(REHA_BERICHT) == HEALTH


# --- Regel-Klassifikator: Gegenproben ---------------------------------


ARZTRECHNUNG = """
Musterpraxis Dr. Muster
Rechnung

Rechnungsnummer: RE-2026-0815
Leistungen nach GOAE
Diagnose: Musterdiagnose
Rechnungsbetrag: 148,50 EUR
"""

ZAHNARZTRECHNUNG = """
Zahnarztpraxis Muster
Rechnung

Rechnungsnummer: ZA-2026-0042
Rechnungsbetrag: 320,00 EUR
"""

BEITRAGSBESCHEINIGUNG = """
Musterkasse - Ihre Krankenkasse

Bescheinigung ueber geleistete Beitraege zur Kranken- und Pflegeversicherung
fuer Ihre Einkommensteuererklaerung

Beitrag zur Krankenversicherung: 4.200,00 EUR
"""

GEHALTSABRECHNUNG_KLINIKUM = """
Musterklinikum GmbH
Gehaltsabrechnung Maerz 2026

Arbeitgeber: Musterklinikum GmbH
Krankenversicherung 4,15 %
Pflegeversicherung 1,70 %
"""


def test_arztrechnung_bleibt_rechnung():
    """Grenze 1 — daran haengt der Steuerzweck krankheitskosten."""
    assert match_rule(ARZTRECHNUNG) == INVOICE


def test_zahnarztrechnung_bleibt_rechnung():
    assert match_rule(ZAHNARZTRECHNUNG) == INVOICE


def test_beitragsbescheinigung_wird_nicht_gesundheit():
    """Grenze 2 — sonst fielen Vorsorgeaufwendungen aus der Erklaerung."""
    assert match_rule(BEITRAGSBESCHEINIGUNG) != HEALTH


def test_klinikum_als_arbeitgeber_bleibt_arbeit():
    """Die Lehre aus ADR 014, uebertragen: Kliniken sind auch Arbeitgeber."""
    assert match_rule(GEHALTSABRECHNUNG_KLINIKUM) == EMPLOYMENT


def test_keine_einrichtungsnamen_unter_den_schluesselwoertern():
    woerter = {wort for wort, _ in KEYWORD_WEIGHTS[HEALTH]}

    assert woerter.isdisjoint(
        {"klinik", "klinikum", "praxis", "krankenhaus", "arzt", "krankenversicherung"}
    )


def test_krankenkasse_entscheidet_nie_allein():
    """Gewicht 1 heisst: MIN_SCORE und die max_weight-Schranke greifen nicht."""
    gewichte = dict(KEYWORD_WEIGHTS[HEALTH])

    assert gewichte.get("krankenkasse", 1) == 1


# --- Steuer, Dateiname, Formular, Anzeige ------------------------------


def test_nicht_steuerrelevant():
    for unterart in sorted(UNTERARTEN):
        assert (
            default_tax_relevance(HEALTH, {"document_subtype": unterart}) is False
        ), unterart


def test_dateiname_traegt_datum_aussteller_betreff():
    name = build_filename(
        {"document_type": HEALTH},
        {
            "document_subtype": "arztunterlagen",
            "issuer": "Musterpraxis",
            "document_date": "12.03.2026",
            "subject": "Befundbericht Knie",
        },
        "scan.pdf",
    )

    # Leerzeichen werden zu Unterstrichen (_clean_name).
    assert name == "2026-03-12_Musterpraxis_Befundbericht_Knie.pdf"


def test_dateiname_faellt_auf_die_unterart_zurueck():
    name = build_filename(
        {"document_type": HEALTH},
        {
            "document_subtype": "impfung",
            "issuer": "Musterpraxis",
            "document_date": "04.05.2026",
        },
        "scan.pdf",
    )

    assert name == "2026-05-04_Musterpraxis_Impfung.pdf"


def test_formular_zeigt_aussteller_datum_betreff():
    felder = [feld["key"] for feld in form_fields(HEALTH)]

    assert felder == ["issuer", "document_date", "subject"]


def test_formularfelder_ueberleben_die_whitelist():
    """Ein Formularfeld, das die Whitelist verwirft, verliert beim Speichern
    still seinen Wert — dieselbe Gegenprobe wie bei education."""
    for unterart in sorted(UNTERARTEN):
        keys = {feld["key"] for feld in form_fields(HEALTH, unterart)}
        erlaubt = set(whitelist_fields(HEALTH, dict.fromkeys(keys, "x")))

        assert keys <= erlaubt | {"document_subtype"}, unterart


def test_anzeigename_nutzt_kurzlabel_und_bei_sonstiges_den_betreff():
    assert (
        get_document_art_label(HEALTH, {"document_subtype": "attest"})
        == "Attest / AU"
    )
    assert (
        get_document_art_label(
            HEALTH,
            {"document_subtype": "sonstiges", "subject": "Kontrolluntersuchung"},
        )
        == "Kontrolluntersuchung"
    )


# --- Prompts -----------------------------------------------------------


def test_extraktionsprompt_ist_verdrahtet_und_nennt_alle_unterarten():
    assert PROMPT_FILES[HEALTH] == "extract_health.txt"

    prompt = (REPO / "src" / "classifier" / "prompts" / "extract_health.txt").read_text(
        encoding="utf-8"
    )

    for unterart in UNTERARTEN:
        assert f'"{unterart}"' in prompt, unterart


def test_klassifikationsprompt_nennt_die_beiden_grenzen():
    prompt = (REPO / "src" / "classifier" / "prompts" / "classify.txt").read_text(
        encoding="utf-8"
    )

    assert "\nhealth\n" in prompt
    # Grenze 1 und 2 muessen dem Modell ausdruecklich gesagt werden.
    assert "Arztrechnung" in prompt
    assert "Beitr" in prompt and "insurance" in prompt

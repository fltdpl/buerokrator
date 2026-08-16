"""Design im Stil von Creative Tims „Paper Dashboard".

Merkmale: linke Seitenleiste, karten-basierter Inhalt, weiche Radien, sehr
dezente Schatten, dünne Überschriften, farbige Akzente.

Farbschema: heller Inhaltsbereich mit dunkler Schrift, dunkle Seitenleiste
mit heller Schrift.

Bewusste Abweichung von der Vorlage: Sie lädt die Schrift „Muli" von Google
Fonts. Das Projekt arbeitet offline und ohne Requests an Dritte — deshalb
der System-Font-Stack. Icons kommen aus den in NiceGUI gebündelten Material
Icons, ebenfalls lokal.
"""

from nicegui import ui

# Vorgegebene Palette.
DARK = "#1e2229"
DARK_ACTIVE = "#f18758"
LIGHT = "#f7f8f6"
ACCENT_A = "#fed9b7"
ACCENT_B = "#f07167"

# Hauptfenster: heller Grund, Karten in Weiß darüber abgesetzt.
BACKGROUND = LIGHT
SURFACE = "#ffffff"
BORDER = "rgba(0, 129, 167, 0.15)"

# Dunkle Schrift auf hellem Grund. Beide Töne sind aus DARK abgedunkelt,
# damit die Schrift zur Palette gehört, statt neutral grau daneben zu stehen.
INK = "#123a47"
INK_MUTED = "#5f7d88"

# Seitenleiste: dunkler Grund, helle Schrift.
SIDEBAR_BACKGROUND = DARK
SIDEBAR_TEXT = LIGHT
SIDEBAR_ACTIVE = DARK_ACTIVE

PRIMARY = DARK
SUCCESS = DARK_ACTIVE
DANGER = ACCENT_B
INFO = DARK_ACTIVE

# ACCENT_A (#fed9b7) ist als Fläche gedacht und hat auf Weiß zu wenig Kontrast
# für Icons oder Text. Für farbige Schrift/Icons deshalb ein abgedunkelter
# Ton derselben Farbe; die helle Originalfarbe bleibt Flächen vorbehalten.
ACCENT_A_INK = "#c07f43"
WARNING = ACCENT_A_INK

# Serienfarben der Analyse-Diagramme (helle Fläche). Als Dreier-Palette
# gegen Farbfehlsichtigkeit und Verwechselbarkeit geprüft (dataviz-
# Validator: CVD-Abstände, Chroma, Lightness ok). Die Koralle liegt unter
# 3:1 Kontrast auf Weiß — deshalb gehören neben das Diagramm immer
# Direktbeschriftung und eine Tabelle mit denselben Werten.
CHART_SERIES = {
    "brutto": "#0081a7",  # Petrol (Farbton der Kartenrahmen)
    "steuern": ACCENT_B,  # Koralle
    "netto": "#008300",  # Grün — „was übrig bleibt"
}
CHART_GRID = "#e4e8e6"  # zurückhaltende Gitterlinien auf Weiß

# Punktfarben der Tags. Nur der PUNKT ist farbig, der Chip bleibt neutral —
# eine Wand getönter Flächen würde das zurückhaltende Layout erschlagen, und
# die Farbe ist ohnehin nur eine Wiedererkennungshilfe: der Name trägt die
# Aussage. Sechs reichen; darüber hinaus wiederholen sie sich.
#
# Kontrast ist hier unkritisch (kein Text auf diesen Farben), Unterscheidbarkeit
# dagegen schon: die sechs Töne sind über den Farbkreis verteilt statt aus
# einer Familie, damit sie auch bei Farbfehlsichtigkeit auseinandergehen.
TAG_COLORS = (
    "#0081a7",  # Petrol (Farbton der Kartenrahmen)
    "#f07167",  # Koralle
    "#008300",  # Grün
    "#c07f43",  # Ocker
    "#7b5ea7",  # Violett
    "#1e2229",  # Anthrazit
)


# Sinnbild je Dokumenttyp (Material Icons, lokal gebündelt). Bewusst OHNE
# eigene Farbe je Kategorie: die Palette hat fünf Akzente, elf bunte Icons
# würden Konfetti — dieselbe Begründung wie beim Tag-Punkt oben. Das Icon
# trägt die Wiedererkennung, die Zahl die Aussage.
DOCUMENT_TYPE_ICONS = {
    "invoice": "receipt_long",
    "tax": "account_balance",
    "insurance": "shield",
    "pension": "savings",
    "bank": "account_balance_wallet",
    "housing": "home",
    "employment": "work",
    "legal": "gavel",
    "education": "school",
    "health": "medical_services",
    "unknown": "help_outline",
}


def tag_color(color_index):
    """Farbe zur gespeicherten laufenden Nummer.

    Die Datenbank speichert nur eine Nummer, keine Farbe — so kann die
    Palette sich ändern, ohne dass Bestandsdaten anzufassen wären.
    """
    try:
        nummer = int(color_index)

    except (TypeError, ValueError):
        nummer = 0

    return TAG_COLORS[nummer % len(TAG_COLORS)]


# Akzentfarbe je Kennzahl-Karte (wie in der Vorlage: farbiges Icon links).
ACCENTS = {
    "primary": PRIMARY,
    "success": SUCCESS,
    "warning": WARNING,
    "danger": DANGER,
    "info": INFO,
}

_CSS = f"""
body, .nicegui-content {{
    background: {BACKGROUND};
    color: {INK};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
    font-weight: 400;
}}

/* Überschriften dünn wie in der Vorlage. */
.page-title {{
    font-weight: 300;
    letter-spacing: 0.02em;
    color: {INK};
}}

.muted {{ color: {INK_MUTED}; }}

/* Wortmarke: gleiche Schrift und Größe wie eine Seitenüberschrift, aber hell
   auf dunklem Grund. Das Padding entspricht dem p-6 des Inhaltsbereichs,
   damit Marke und Seitenüberschrift auf einer Linie sitzen. */
.brand {{
    color: {SIDEBAR_TEXT};
    padding: 1.5rem;
    line-height: 1.2;
    white-space: nowrap;
}}

/* Karten: weicher Radius, kaum Schatten, feine Kante statt harter Trennung. */
.paper-card, .q-card {{
    background: {SURFACE};
    color: {INK};
    border: 1px solid {BORDER};
    border-radius: 8px;
    box-shadow: 0 1px 15px 1px rgba(18, 58, 71, 0.06);
}}

/* Karte, die irgendwohin führt (Dashboard-Kacheln). `cursor-pointer` allein
   sieht man erst, wenn der Zeiger schon darauf steht — die Kachel soll aber
   von sich aus als Weg zu erkennen sein. Deshalb ein Rahmen im Akzentton
   beim Überfahren; die Fläche bleibt ruhig. */
.paper-card.klickbar:hover {{
    border-color: {DARK_ACTIVE};
    box-shadow: 0 2px 18px 1px rgba(18, 58, 71, 0.12);
}}

/* Seitenleiste: dunkler Grund, helle Schrift, aktiver Eintrag abgesetzt. */
.sidebar {{
    background: {SIDEBAR_BACKGROUND};
    color: {SIDEBAR_TEXT};
    border-right: none;
}}

.nav-item {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0.9rem;
    margin: 0.15rem 0.6rem;
    border-radius: 6px;
    color: {SIDEBAR_TEXT};
    opacity: 0.8;
    text-decoration: none;
    transition: background 0.2s, opacity 0.2s;
}}

/* Nutzerprofil unter der Wortmarke. Linksbündig zu den Navigationspunkten:
   deren Inhalt beginnt bei 0.6rem Rand + 0.9rem Innenabstand = 1.5rem,
   genau wie die Wortmarke. */
.profile-block {{
    padding: 0 0.9rem 0.1rem;
    margin: 0 0.6rem;
    color: {SIDEBAR_TEXT};
}}

.profile-block .profile-role {{
    opacity: 0.55;
}}

/* Umschalter neben dem Namen: zurückhaltend, bis man ihn sucht. */
.profile-switch {{
    opacity: 0.6;
    transition: opacity 0.2s;
}}

.profile-switch:hover {{ opacity: 1; }}

/* Trennt „wer bin ich" von „wohin gehe ich". Bewusst zurückhaltend: eine
   kräftige Linie zerschnitte die Seitenleiste in zwei Blöcke. */
.sidebar-divider {{
    /* align-self/flex-shrink sind hier nicht kosmetisch: der Drawer-Inhalt
       ist eine Flex-Spalte. Ohne stretch bekäme das leere div die Breite 0,
       ohne shrink:0 drückt der Überlauf seine Höhe auf 0 — beides macht die
       Linie unsichtbar, obwohl sie im DOM steht. */
    align-self: stretch;
    flex: 0 0 1px;
    height: 1px;
    min-height: 1px;
    background: rgba(253, 252, 220, 0.28);
    margin: 0.5rem 1.5rem 0.6rem;
}}

.nav-item:hover {{
    background: rgba(253, 252, 220, 0.12);
    opacity: 1;
}}

.nav-item.active {{
    background: {SIDEBAR_ACTIVE};
    color: #ffffff;
    opacity: 1;
}}

/* Tabellen: heller Grund, Kopfzeile klein und gedämpft. */
.q-table__container, .q-table thead th, .q-table tbody td {{
    background: {SURFACE};
    color: {INK};
}}

.q-table thead th {{
    color: {INK_MUTED};
    font-weight: 400;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
}}

.q-table tbody tr:hover {{ background: {LIGHT}; }}

.q-field--outlined .q-field__control {{ border-radius: 6px; }}

/* Tag-Chips. Der Selektor führt .q-chip mit, weil Quasars eigene
   Chip-Farbe sonst gewinnt — ein Inline-Style am Element reicht dafür
   nicht (dunkler Grund auf dunkler Schrift, real passiert). */
.q-chip.tag-chip {{
    background: {SURFACE};
    color: {INK};
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 400;
}}

/* Der farbige Punkt vor dem Namen — die einzige Farbe am Tag. Quasar
   rendert ihn als führendes Icon (.q-chip__icon--left); ohne diese Regel
   erbt er die Schriftfarbe des Chips und alle Punkte sehen gleich aus. */
.q-chip.tag-chip .q-chip__icon--left {{
    color: var(--tag-color, {INK_MUTED});
    font-size: 0.6rem;
    margin-right: 0.35rem;
    opacity: 1;
}}

/* Das Entfernen-Kreuz erbt sonst eine Farbe, die auf der hellen Tönung
   kaum zu sehen ist. */
.q-chip.tag-chip .q-chip__icon--remove {{
    color: {INK_MUTED};
    opacity: 1;
}}

.q-chip.tag-chip .q-chip__icon--remove:hover {{ color: {DANGER}; }}
"""


def apply_theme():
    """Helles Theme, Quasar-Farben und das eigene Stylesheet setzen."""
    ui.dark_mode().disable()
    ui.colors(
        primary=PRIMARY,
        secondary=DARK_ACTIVE,
        accent=ACCENT_B,
        positive=SUCCESS,
        negative=DANGER,
        warning=ACCENT_A,
        dark=DARK,
    )
    ui.add_css(_CSS)

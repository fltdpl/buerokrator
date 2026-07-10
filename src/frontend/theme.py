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

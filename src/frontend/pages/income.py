"""Tab „Einkommen" der Analyse-Seite: Jahreseinkommen über die Jahre.

Nur Darstellung — die Zahlen kommen aus services.income_service, das SVG
aus frontend.chart. Dieselbe Herleitbarkeits-Philosophie wie beim
Steuer-Tab: jede Jahreszeile lässt sich zu ihren Belegen aufklappen.
"""

from nicegui import ui

from src.frontend.chart import line_chart_svg
from src.frontend.layout import format_euro
from src.frontend.theme import CHART_SERIES
from src.services.income_service import build_income_series

SERIES_LABELS = {
    "brutto": "Brutto",
    "steuern": "Steuern",
    "netto": "rechnerisches Netto",
}


def _chart_series(entries):
    return [
        {
            "label": SERIES_LABELS[key],
            # Kurzform am Linienende ("rechnerisches Netto" liefe über den
            # Rand); die Legende trägt den vollen Namen.
            "short": key.capitalize(),
            "color": CHART_SERIES[key],
            "values": {e["year"]: e[key] for e in entries},
        }
        for key in ("brutto", "steuern", "netto")
    ]


def _year_details(entry):
    """Aufklappbare Beleg-Herleitung einer Jahreszeile."""
    for ref in entry["documents"]:
        ui.link(
            f"• {ref['employer'] or ref['filename']}",
            f"/dokumente/{ref['id']}",
        ).classes("text-sm")

    for ref in entry["pending"]:
        ui.link(
            f"• 🟡 {ref['employer'] or ref['filename']} — ungeprüft, "
            "zählt nicht",
            f"/dokumente/{ref['id']}",
        ).classes("text-sm")

    for ref in entry["missing_value"]:
        ui.link(
            f"• ⚠️ {ref['employer'] or ref['filename']} — ohne "
            "Bruttoarbeitslohn, zählt nicht",
            f"/dokumente/{ref['id']}",
        ).classes("text-sm")


def render_income_tab():
    entries = build_income_series()

    if not entries:
        ui.label(
            "Noch keine geprüften Lohnsteuerbescheinigungen vorhanden — "
            "die Einkommens-Auswertung baut auf ihnen auf."
        ).classes("muted")
        return

    with ui.card().classes("w-full"):
        ui.label("Jahreseinkommen").classes("text-xl page-title")
        ui.label(
            "Aus den geprüften Lohnsteuerbescheinigungen; mehrere "
            "Bescheinigungen eines Jahres addieren sich. Das rechnerische "
            "Netto ist Brutto abzüglich Steuern und Arbeitnehmer-"
            "Sozialabgaben — das tatsächlich ausgezahlte Netto kann "
            "abweichen (z. B. VWL, betriebliche Altersvorsorge)."
        ).classes("text-sm muted")

        # Legende: farbige Marke trägt die Farbe, der Text bleibt Textfarbe.
        with ui.row().classes("gap-4 items-center"):
            for key in ("brutto", "steuern", "netto"):
                with ui.row().classes("gap-1 items-center no-wrap"):
                    ui.html(
                        '<span style="display:inline-block;width:14px;'
                        "height:3px;border-radius:2px;background:"
                        f'{CHART_SERIES[key]}"></span>'
                    )
                    ui.label(SERIES_LABELS[key]).classes("text-sm")

        ui.html(line_chart_svg(_chart_series(entries))).classes("w-full")

    with ui.card().classes("w-full"):
        ui.label("Werte je Jahr").classes("text-xl page-title")

        for entry in entries:
            counted = len(entry["documents"])
            notes = []

            if entry["pending"]:
                notes.append(f"🟡 {len(entry['pending'])} ungeprüft")

            if entry["missing_value"]:
                notes.append(
                    f"⚠️ {len(entry['missing_value'])} ohne Bruttowert"
                )

            note_text = f"  ·  {' · '.join(notes)}" if notes else ""
            header = (
                f"{entry['year']}  —  Brutto {format_euro(entry['brutto'])}"
                f"  ·  Steuern {format_euro(entry['steuern'])}"
                f"  ·  Netto {format_euro(entry['netto'])}"
                f"  ·  {counted} Beleg(e){note_text}"
            )

            with ui.expansion(header).classes("w-full"):
                _year_details(entry)

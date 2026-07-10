from nicegui import ui

from src.core.document_types import (
    DOCUMENT_TYPE_LABELS,
    INSURANCE,
    INVOICE,
    PENSION,
    TAX,
)
from src.frontend.layout import card, page_layout
from src.frontend.theme import ACCENTS, INK_MUTED
from src.services.stats_service import get_dashboard_data


def _metric(label, value, icon, accent="primary"):
    """Kennzahl-Karte: farbiges Icon links, Zahl und Bezeichnung rechts."""
    with card("flex-grow"):
        with ui.row().classes("items-center gap-4 no-wrap"):
            ui.icon(icon).classes("text-4xl").style(f"color: {ACCENTS[accent]}")

            with ui.column().classes("gap-0"):
                ui.label(str(value)).classes("text-3xl font-light leading-none")
                ui.label(label).classes("text-sm").style(f"color: {INK_MUTED}")


@ui.page("/")
def dashboard_page():
    stats = get_dashboard_data()
    counts = stats["counts_by_type"]

    with page_layout("Dashboard"):
        ui.label("Dashboard").classes("text-3xl page-title")
        ui.label(f"{stats['total']} Dokumente archiviert").classes("muted")

        # Übernimmt auch die Zahlen der alten Analyse-Seite (entfällt).
        with ui.row().classes("gap-4 w-full no-wrap"):
            _metric("Dokumente", stats["total"], "folder", "primary")
            _metric("Rechnungen", counts.get(INVOICE, 0), "receipt_long", "warning")
            _metric("Versicherungen", counts.get(INSURANCE, 0), "shield", "info")
            _metric("Vorsorge", counts.get(PENSION, 0), "savings", "success")
            _metric("Steuern", counts.get(TAX, 0), "account_balance", "danger")

        # Aufgaben: die beiden Dinge, die tatsächlich Arbeit bedeuten —
        # Inbox importieren und ungeprüfte Dokumente durchsehen.
        with card("w-full"):
            ui.label("Aufgaben").classes("text-xl page-title")

            if stats["unverified_count"] or stats["inbox_count"]:
                with ui.row().classes("gap-4"):
                    if stats["unverified_count"]:
                        first_id = stats["first_unverified_id"]
                        ui.button(
                            f"{stats['unverified_count']} ungeprüfte Dokumente prüfen",
                            icon="fact_check",
                            on_click=lambda: ui.navigate.to(f"/dokumente/{first_id}"),
                        ).props("color=primary unelevated")

                    if stats["inbox_count"]:
                        ui.button(
                            f"{stats['inbox_count']} Datei(en) in der Inbox importieren",
                            icon="file_upload",
                            on_click=lambda: ui.navigate.to("/import"),
                        ).props("outline color=primary")

            else:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle").style(f"color: {ACCENTS['success']}")
                    ui.label("Keine offenen Aufgaben — Inbox leer, alles geprüft.")

        with card("w-full"):
            ui.label("Zuletzt archiviert").classes("text-xl page-title")

            for row in stats["recent"]:
                document_id = row["id"]
                filename = row["filename"]
                document_type = row["document_type"]
                type_label = DOCUMENT_TYPE_LABELS.get(document_type, document_type)

                with ui.row().classes("gap-2 items-center"):
                    ui.label(type_label).classes("text-sm w-32").style(
                        f"color: {INK_MUTED}"
                    )
                    ui.link(filename, f"/dokumente/{document_id}")

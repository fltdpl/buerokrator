from nicegui import ui

from src.core.document_types import DOCUMENT_TYPE_LABELS, INSURANCE, INVOICE, PENSION
from src.frontend.layout import page_layout
from src.services.stats_service import get_dashboard_data


def _metric(label, value):
    with ui.card().classes("items-center min-w-40"):
        ui.label(str(value)).classes("text-3xl font-bold")
        ui.label(label).classes("text-sm text-gray-500")


@ui.page("/")
def dashboard_page():
    stats = get_dashboard_data()
    counts = stats["counts_by_type"]

    with page_layout("Dashboard"):
        ui.label("Dashboard").classes("text-2xl font-bold")
        ui.label(f"{stats['total']} Dokumente archiviert").classes("text-gray-500")

        with ui.row().classes("gap-4"):
            _metric("Dokumente", stats["total"])
            _metric("Rechnungen", counts.get(INVOICE, 0))
            _metric("Versicherungen", counts.get(INSURANCE, 0))
            _metric("Vorsorge", counts.get(PENSION, 0))

        # Aufgaben: die beiden Dinge, die tatsächlich Arbeit bedeuten —
        # Inbox importieren und ungeprüfte Dokumente durchsehen.
        if stats["unverified_count"] or stats["inbox_count"]:
            ui.label("Aufgaben").classes("text-xl font-bold mt-4")

            with ui.row().classes("gap-4"):
                if stats["unverified_count"]:
                    first_id = stats["first_unverified_id"]
                    ui.button(
                        f"🟡 {stats['unverified_count']} ungeprüfte Dokumente prüfen",
                        on_click=lambda: ui.navigate.to(f"/dokumente/{first_id}"),
                    ).props("color=primary")

                if stats["inbox_count"]:
                    ui.button(
                        f"📥 {stats['inbox_count']} Datei(en) in der Inbox importieren",
                        on_click=lambda: ui.navigate.to("/import"),
                    ).props("outline")

        else:
            ui.label("✅ Keine offenen Aufgaben — Inbox leer, alles geprüft.").classes(
                "text-green-700"
            )

        ui.label("Zuletzt archiviert").classes("text-xl font-bold mt-4")

        for row in stats["recent"]:
            document_id, filename, document_type = row[0], row[1], row[2]
            type_label = DOCUMENT_TYPE_LABELS.get(document_type, document_type)

            with ui.row().classes("gap-2 items-center"):
                ui.label(type_label).classes("text-gray-500 text-sm w-32")
                ui.link(filename, f"/dokumente/{document_id}")

from nicegui import ui

from src.core.document_types import DOCUMENT_TYPES, DOCUMENT_TYPE_LABELS
from src.database.export_csv import export_documents_csv
from src.database.list_documents import list_documents
from src.database.search import search_documents
from src.database.statistics import get_verification_statistics
from src.frontend.layout import card, format_euro, page_layout
from src.services.document_service import (
    available_years,
    build_table_rows,
    filter_documents,
    move_documents_to_trash,
    reclassify_documents,
)

COLUMNS = [
    {"name": "id", "label": "ID", "field": "id", "sortable": True, "align": "left"},
    {"name": "status", "label": "", "field": "status", "align": "center"},
    {"name": "year", "label": "Jahr", "field": "year", "sortable": True, "align": "left"},
    {"name": "art_label", "label": "Dokument", "field": "art_label", "sortable": True, "align": "left"},
    {"name": "category", "label": "Kategorie", "field": "category", "sortable": True, "align": "left"},
    {"name": "issuer", "label": "Aussteller", "field": "issuer", "sortable": True, "align": "left"},
    {"name": "amount", "label": "Betrag", "field": "amount", "sortable": True, "align": "right", ":sort": "(a, b, rowA, rowB) => (rowA.amount_raw ?? -1) - (rowB.amount_raw ?? -1)"},
    {"name": "created_at", "label": "Importiert", "field": "created_at", "sortable": True, "align": "left"},
]


def _table_rows(documents):
    rows = []

    for row in build_table_rows(documents):
        rows.append(
            {
                "id": row["id"],
                "status": "🟢" if row["verified"] else "🟡",
                "year": str(row["year"]) if row["year"] else "-",
                "art_label": row["art_label"],
                "category": DOCUMENT_TYPE_LABELS.get(
                    row["document_type"], row["document_type"]
                ),
                "issuer": row["issuer"],
                "amount": format_euro(row["amount"]) if row["amount"] is not None else "",
                "amount_raw": row["amount"],
                "created_at": row["created_at"],
            }
        )

    return rows


def _default_filters():
    return {
        "search": "",
        "type": "Alle",
        "status": "Alle",
        "year_range": None,
        "issuer": "",
        "filename": "",
    }


# Modul-global: die Filter bleiben beim Wechsel in die Detailansicht und zurück
# erhalten (überleben Navigation, setzen sich beim App-Neustart zurück). Für
# den lokalen Ein-Nutzer-Betrieb bewusst einfach gehalten.
_FILTER_STATE = _default_filters()


@ui.page("/dokumente")
def documents_page():
    filters = _FILTER_STATE

    all_years = available_years(list_documents())

    def filtered_documents():
        documents = (
            search_documents(filters["search"])
            if filters["search"]
            else list_documents()
        )

        year_range = filters["year_range"]
        from_year = to_year = None

        # Jahr-Filter nur anwenden, wenn der Regler nicht die volle
        # Spannweite abdeckt (volle Spannweite = kein Filter).
        if year_range and all_years:
            if year_range["min"] > all_years[0]:
                from_year = int(year_range["min"])

            if year_range["max"] < all_years[-1]:
                to_year = int(year_range["max"])

        return filter_documents(
            documents,
            document_type=None if filters["type"] == "Alle" else filters["type"],
            verified=None
            if filters["status"] == "Alle"
            else filters["status"] == "Geprüft",
            from_year=from_year,
            to_year=to_year,
            issuer=filters["issuer"],
            filename=filters["filename"],
        )

    @ui.refreshable
    def results():
        documents = filtered_documents()
        rows = _table_rows(documents)

        with ui.row().classes("items-center gap-4 w-full"):
            ui.label(f"{len(rows)} Dokumente gefunden").classes("muted")

            ui.button(
                "📥 CSV Export",
                on_click=lambda: ui.download(
                    export_documents_csv(documents).encode("utf-8"),
                    "buerokrator_export.csv",
                ),
            ).props("flat dense")

        if not rows:
            ui.label("Keine Dokumente gefunden.")
            return

        table = ui.table(
            columns=COLUMNS,
            rows=rows,
            row_key="id",
            pagination=25,
            selection="multiple",
        ).classes("w-full")

        # Zeilenklick öffnet das Detail; die Auswahl läuft über die Checkbox,
        # damit ein Klick nicht beides bedeutet.
        table.on(
            "rowClick",
            lambda event: ui.navigate.to(f"/dokumente/{event.args[1]['id']}"),
        )

        bulk_actions(table)

    def bulk_actions(table):
        """Aktionen für die ausgewählten Zeilen (nur sichtbar, wenn ausgewählt)."""
        def selected_ids():
            return [row["id"] for row in table.selected]

        def delete_selected():
            deleted = move_documents_to_trash(selected_ids())
            delete_dialog.close()
            ui.notify(f"{deleted} Dokument(e) in den Papierkorb verschoben.")
            results.refresh()

        def reclassify_selected(document_type):
            changed = reclassify_documents(selected_ids(), document_type)
            ui.notify(
                f"{changed} Dokument(e) auf "
                f"{DOCUMENT_TYPE_LABELS.get(document_type, document_type)} gesetzt "
                "und zum erneuten Prüfen markiert."
            )
            results.refresh()

        with ui.dialog() as delete_dialog, ui.card():
            confirm_label = ui.label("")

            with ui.row().classes("justify-end w-full"):
                ui.button("Abbrechen", on_click=delete_dialog.close).props("flat")
                ui.button("Ja, löschen", on_click=delete_selected).props(
                    "color=negative"
                )

        def open_delete_dialog():
            confirm_label.text = (
                f"{len(table.selected)} Dokument(e) in den Papierkorb verschieben?"
            )
            delete_dialog.open()

        with ui.row().classes("items-center gap-3").bind_visibility_from(
            table, "selected", backward=bool
        ):
            ui.label().bind_text_from(
                table, "selected", lambda rows: f"{len(rows)} ausgewählt"
            ).classes("muted")

            ui.select(
                {dtype: DOCUMENT_TYPE_LABELS.get(dtype, dtype) for dtype in DOCUMENT_TYPES},
                label="Umklassifizieren nach",
                on_change=lambda event: reclassify_selected(event.value),
            ).props("dense").classes("w-56")

            ui.button("🗑 Auswahl löschen", on_click=open_delete_dialog).props(
                "flat dense color=negative"
            )

    def set_filter(key, value):
        filters[key] = value
        results.refresh()

    def reset_filters():
        filters.update(_default_filters())
        filter_bar.refresh()
        results.refresh()

    @ui.refreshable
    def filter_bar():
        with ui.row().classes("items-end gap-4 w-full"):
            ui.input(
                "Volltext",
                value=filters["search"],
                on_change=lambda event: set_filter("search", event.value),
            ).props("dense clearable").classes("w-48")

            ui.select(
                ["Alle", *DOCUMENT_TYPES],
                value=filters["type"],
                label="Kategorie",
                on_change=lambda event: set_filter("type", event.value),
            ).props("dense").classes("w-36")

            ui.select(
                ["Alle", "Ungeprüft", "Geprüft"],
                value=filters["status"],
                label="Status",
                on_change=lambda event: set_filter("status", event.value),
            ).props("dense").classes("w-36")

            ui.input(
                "Aussteller",
                value=filters["issuer"],
                on_change=lambda event: set_filter("issuer", event.value),
            ).props("dense clearable").classes("w-40")

            ui.input(
                "Dateiname",
                value=filters["filename"],
                on_change=lambda event: set_filter("filename", event.value),
            ).props("dense clearable").classes("w-40")

            if len(all_years) > 1:
                year_range = filters["year_range"] or {
                    "min": all_years[0],
                    "max": all_years[-1],
                }
                with ui.column().classes("w-56 gap-0"):
                    ui.label("Jahre").classes("text-xs muted")
                    ui.range(
                        min=all_years[0],
                        max=all_years[-1],
                        value=year_range,
                        on_change=lambda event: set_filter("year_range", event.value),
                    ).props("label dense")

            ui.button("Filter zurücksetzen", on_click=reset_filters).props(
                "flat dense"
            )

    unverified, verified = get_verification_statistics()

    with page_layout("Dokumente"):
        ui.label("Dokumente").classes("text-3xl page-title")
        ui.label(f"🟡 {unverified} ungeprüft · 🟢 {verified} geprüft").classes("muted")

        with card("w-full"):
            filter_bar()

        with card("w-full"):
            results()

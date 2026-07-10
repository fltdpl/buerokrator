from nicegui import ui

from src.frontend.layout import card, page_layout
from src.services.trash_service import empty_trash, list_trash, restore_from_trash


def _format_size(size):
    if size < 1024:
        return f"{size} B"

    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"

    return f"{size / 1024 / 1024:.1f} MB"


def render_trash():
    """Papierkorb-Inhalt (ohne Seitenrahmen) — nutzbar in Route und Settings-Tab."""
    ui.label(
        "Gelöschte Dokumente liegen hier als Datei. Wiederherstellen legt "
        "sie zurück in die Inbox — der Import archiviert sie danach neu."
    ).classes("muted")

    @ui.refreshable
    def trash_area():
        entries = list_trash()

        if not entries:
            ui.label("Der Papierkorb ist leer.").classes("muted")
            return

        def restore(name):
            target = restore_from_trash(name)
            ui.notify(
                f"{name} liegt wieder in der Inbox."
                if target
                else f"{name} nicht gefunden.",
                type="positive" if target else "warning",
            )
            trash_area.refresh()

        for entry in entries:
            with ui.row().classes("items-center gap-4 w-full"):
                ui.label(entry["name"]).classes("flex-grow")
                ui.label(_format_size(entry["size"])).classes(
                    "text-sm muted w-20 text-right"
                )
                ui.label(entry["deleted_at"]).classes("text-sm muted w-36")
                ui.button(
                    "↩️ Wiederherstellen",
                    on_click=lambda _, name=entry["name"]: restore(name),
                ).props("flat dense")

        ui.separator()

        with ui.dialog() as empty_dialog, ui.card():
            ui.label(
                f"{len(entries)} Datei(en) endgültig löschen?"
            ).classes("font-bold")
            ui.label("Dieser Schritt kann nicht rückgängig gemacht werden.")

            def do_empty():
                removed = empty_trash()
                empty_dialog.close()
                ui.notify(f"{removed} Datei(en) endgültig gelöscht.", type="positive")
                trash_area.refresh()

            with ui.row().classes("justify-end w-full"):
                ui.button("Abbrechen", on_click=empty_dialog.close).props("flat")
                ui.button("Endgültig löschen", on_click=do_empty).props(
                    "color=negative"
                )

        ui.button("🔥 Papierkorb leeren", on_click=empty_dialog.open).props(
            "color=negative outline"
        )

    with card("w-full"):
        trash_area()


@ui.page("/papierkorb")
def trash_page():
    with page_layout("Papierkorb"):
        ui.label("🗑 Papierkorb").classes("text-3xl page-title")
        render_trash()

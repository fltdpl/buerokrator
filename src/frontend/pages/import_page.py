from pathlib import Path

from nicegui import run, ui

from src.core.document_types import DOCUMENT_TYPE_LABELS
from src.database.list_documents import get_next_unverified_id
from src.frontend.layout import card, page_layout
from src.processor.batch_import import (
    find_inbox_documents,
    import_inbox_documents,
)


@ui.page("/import")
def import_page():
    with page_layout("Import"):
        ui.label("Dokument importieren").classes("text-3xl page-title")

        # ------------------------------------------------------------
        # Stapel-Import
        # ------------------------------------------------------------
        with card("w-full"):
            ui.label("📦 Stapel-Import").classes("text-xl page-title")
            ui.label(
                "Verarbeitet alle Dateien im Inbox-Ordner automatisch: "
                "klassifizieren, umbenennen, archivieren. Die Korrektur der "
                "erkannten Werte passiert danach im Prüf-Workflow."
            ).classes("muted")

            @ui.refreshable
            def import_area():
                pending = find_inbox_documents()

                if not pending:
                    ui.label("Keine Dateien im Inbox-Ordner.").classes("muted")
                    return

                ui.label(f"{len(pending)} Datei(en) im Inbox-Ordner:")

                for path in pending:
                    ui.label(f"• {path.name}").classes("text-sm muted")

                progress_bar = ui.linear_progress(value=0, show_value=False).classes(
                    "w-full"
                )
                progress_bar.set_visibility(False)
                status_label = ui.label("")
                results_column = ui.column().classes("gap-1 w-full")

                async def start_import():
                    start_button.disable()
                    progress_bar.set_visibility(True)

                    def on_progress(index, total, filename):
                        progress_bar.value = index / total if total else 0.0
                        status_label.text = f"Verarbeite {index + 1}/{total}: {filename}"

                    # io_bound: OCR + LLM blockieren sonst die Event-Loop.
                    succeeded, duplicates, failed = await run.io_bound(
                        import_inbox_documents, on_progress
                    )

                    progress_bar.value = 1.0
                    status_label.text = ""

                    with results_column:
                        ui.label(
                            f"✅ {len(succeeded)} Dokument(e) archiviert."
                        ).classes("text-green-700")

                        for result in succeeded:
                            type_label = DOCUMENT_TYPE_LABELS.get(
                                result["document_type"], result["document_type"]
                            )
                            ui.label(
                                f"• {result['source_name']} → {type_label} · "
                                f"{result['filename']}"
                            ).classes("text-sm muted")

                        if duplicates:
                            ui.label(
                                f"♻️ {len(duplicates)} Dublette(n) übersprungen "
                                "(liegen im Papierkorb):"
                            ).classes("text-amber-700")

                            for result in duplicates:
                                with ui.row().classes("items-center gap-1"):
                                    ui.label(
                                        f"• {result['source_name']} ist bereits"
                                        " archiviert als"
                                    ).classes("text-sm muted")
                                    ui.link(
                                        result["duplicate_filename"],
                                        f"/dokumente/{result['duplicate_of']}",
                                    ).classes("text-sm")

                        if failed:
                            ui.label(
                                f"❌ {len(failed)} Dokument(e) fehlgeschlagen:"
                            ).classes("text-red-600")

                            for name in failed:
                                ui.label(f"• {name}").classes("text-sm text-red-600")

                        next_id = get_next_unverified_id()

                        if next_id is not None:
                            ui.button(
                                "✅ Jetzt prüfen",
                                on_click=lambda: ui.navigate.to(
                                    f"/dokumente/{next_id}"
                                ),
                            ).props("color=primary unelevated")

                start_button = ui.button(
                    "Alle importieren",
                    on_click=start_import,
                ).props("color=primary unelevated")

            import_area()

        # ------------------------------------------------------------
        # Upload in die Inbox (der einzige Verarbeitungsweg bleibt der
        # Stapel-Import — Upload legt Dateien nur dorthin).
        # ------------------------------------------------------------
        with card("w-full"):
            ui.label("⬆️ Dateien hochladen").classes("text-xl page-title")
            ui.label(
                "Legt die Dateien in den Inbox-Ordner für den Stapel-Import."
            ).classes("muted")

            async def handle_upload(event):
                inbox = Path("inbox")
                inbox.mkdir(exist_ok=True)

                # Nur den Dateinamen verwenden (keine Pfadanteile aus dem Client).
                name = Path(event.file.name).name
                await event.file.save(inbox / name)

                ui.notify(f"{name} in der Inbox")
                import_area.refresh()

            ui.upload(
                multiple=True,
                auto_upload=True,
                on_upload=handle_upload,
                label="PDF oder Bild auswählen",
            ).props('accept=".pdf,.png,.jpg,.jpeg"').classes("w-full max-w-xl")

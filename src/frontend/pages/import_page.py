from pathlib import Path

from nicegui import run, ui

from src.core.config import load_config
from src.core.document_types import DOCUMENT_TYPE_LABELS
from src.core.logger import logger
from src.database.list_documents import get_next_unverified_id
from src.frontend.layout import card, page_layout
from src.processor.batch_import import (
    find_inbox_documents,
    import_inbox_documents,
)
from src.services import import_job


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
                "erkannten Werte passiert danach im Prüf-Workflow. Der Import "
                "läuft im Hintergrund weiter, auch wenn du die Seite wechselst."
            ).classes("muted")

            def render_result(result):
                ui.label(
                    f"✅ {len(result['succeeded'])} Dokument(e) archiviert."
                ).classes("text-green-700")

                # "none" = Ollama war beim Import nicht erreichbar.
                limited = [
                    entry
                    for entry in result["succeeded"]
                    if entry.get("classification_source") == "none"
                ]

                if limited:
                    ui.label(
                        f"⚠️ {len(limited)} Dokument(e) ohne automatische"
                        " Analyse archiviert (Ollama nicht erreichbar) —"
                        " Typ und Felder bitte im Prüf-Workflow nachtragen"
                        " oder später „Erneut prüfen“ nutzen."
                    ).classes("text-orange-700")

                for entry in result["succeeded"]:
                    type_label = DOCUMENT_TYPE_LABELS.get(
                        entry["document_type"], entry["document_type"]
                    )
                    ui.label(
                        f"• {entry['source_name']} → {type_label} · "
                        f"{entry['filename']}"
                    ).classes("text-sm muted")

                if result["duplicates"]:
                    ui.label(
                        f"♻️ {len(result['duplicates'])} Dublette(n) übersprungen "
                        "(liegen im Papierkorb):"
                    ).classes("text-amber-700")

                    for entry in result["duplicates"]:
                        with ui.row().classes("items-center gap-1"):
                            ui.label(
                                f"• {entry['source_name']} ist bereits"
                                " archiviert als"
                            ).classes("text-sm muted")
                            ui.link(
                                entry["duplicate_filename"],
                                f"/dokumente/{entry['duplicate_of']}",
                            ).classes("text-sm")

                if result["failed"]:
                    ui.label(
                        f"❌ {len(result['failed'])} Dokument(e) fehlgeschlagen:"
                    ).classes("text-red-600")

                    for name in result["failed"]:
                        ui.label(f"• {name}").classes("text-sm text-red-600")

                next_id = get_next_unverified_id()

                with ui.row().classes("gap-2"):
                    if next_id is not None:
                        ui.button(
                            "✅ Jetzt prüfen",
                            on_click=lambda: ui.navigate.to(f"/dokumente/{next_id}"),
                        ).props("color=primary unelevated")

                    ui.button(
                        "Neuer Import",
                        on_click=lambda: (
                            import_job.clear_result(),
                            import_area.refresh(),
                        ),
                    ).props("flat")

            @ui.refreshable
            def import_area():
                state = import_job.get_state()

                # Läuft der Import bereits (von dieser oder einer anderen
                # Seite gestartet): Fortschritt anzeigen und per Timer aus
                # dem geteilten Job-State aktuell halten.
                if state["running"]:
                    total = state["total"]
                    index = state["index"]

                    ui.label(
                        f"Import läuft: {index + 1}/{total}" if total else "Import läuft …"
                    )
                    progress_bar = ui.linear_progress(
                        value=(index / total) if total else 0.0,
                        show_value=False,
                    ).classes("w-full")
                    status_label = ui.label(state["current_filename"])

                    def poll():
                        current = import_job.get_state()

                        if not current["running"]:
                            import_area.refresh()
                            return

                        current_total = current["total"]
                        current_index = current["index"]
                        progress_bar.value = (
                            (current_index / current_total) if current_total else 0.0
                        )
                        status_label.text = current["current_filename"]

                    ui.timer(0.5, poll)
                    return

                # Fehlgeschlagener Lauf: Fehler anzeigen, Neustart anbieten.
                if state["error"]:
                    ui.label(
                        f"❌ Import abgebrochen: {state['error']}"
                    ).classes("text-red-600")
                    ui.button(
                        "Neuer Import",
                        on_click=lambda: (
                            import_job.clear_result(),
                            import_area.refresh(),
                        ),
                    ).props("flat")
                    return

                # Zuletzt beendeter Lauf: Ergebnis zeigen, bis "Neuer Import".
                if state["result"] is not None:
                    render_result(state["result"])
                    return

                pending = find_inbox_documents()

                if not pending:
                    ui.label("Keine Dateien im Inbox-Ordner.").classes("muted")
                    return

                ui.label(f"{len(pending)} Datei(en) im Inbox-Ordner:")

                for path in pending:
                    ui.label(f"• {path.name}").classes("text-sm muted")

                async def start_import():
                    try:
                        import_job.start()
                    except RuntimeError:
                        ui.notify("Es läuft bereits ein Import.")
                        import_area.refresh()
                        return

                    import_area.refresh()

                    def on_progress(index, total, filename):
                        import_job.update_progress(index, total, filename)

                    # io_bound: OCR + LLM blockieren sonst die Event-Loop.
                    # Läuft in NiceGUIs app-globalem Hintergrund-Task, also
                    # unabhängig vom Client, der ihn gestartet hat.
                    # Ohne except bliebe bei einer Exception running=True
                    # stehen und würde jeden weiteren Import blockieren.
                    try:
                        succeeded, duplicates, failed = await run.io_bound(
                            import_inbox_documents, on_progress
                        )

                    except Exception as error:
                        logger.exception("Stapel-Import fehlgeschlagen")
                        import_job.abort(error)

                    else:
                        import_job.finish(succeeded, duplicates, failed)

                    import_area.refresh()

                ui.button(
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
                # Derselbe Inbox-Pfad wie beim Stapel-Import (aus der Config) —
                # sonst landen Uploads bei geändertem Pfad im falschen Ordner.
                inbox = Path(load_config()["paths"]["inbox"])
                inbox.mkdir(parents=True, exist_ok=True)

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

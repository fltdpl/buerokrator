from nicegui import ui

from src.core.config import load_config, save_config
from src.database.reset_database import reset_database_and_archive
from src.frontend.layout import card, page_layout
from src.services.log_service import LOG_LEVELS, read_log_tail
from src.services.model_service import list_installed_models


@ui.page("/einstellungen")
def settings_page():
    config = load_config()

    with page_layout("Einstellungen"):
        ui.label("Einstellungen").classes("text-3xl page-title")

        # ------------------------------------------------------------
        # Konfiguration
        # ------------------------------------------------------------
        current_model = config["classifier"]["model"]
        model_options = list_installed_models(current_model)

        with card("w-full"), ui.row().classes("gap-8 w-full items-start"):
            with ui.column().classes("gap-3 w-96"):
                ui.label("Klassifikation").classes("text-xl page-title")

                model = ui.select(
                    model_options,
                    value=current_model,
                    label="LLM Modell",
                ).classes("w-full")

                temperature = ui.number(
                    "Temperatur",
                    value=float(config["classifier"]["temperature"]),
                    min=0.0,
                    max=1.0,
                    step=0.05,
                ).classes("w-full")

                max_input_chars = ui.number(
                    "Max Input Chars",
                    value=int(config["classifier"]["max_input_chars"]),
                    min=100,
                    max=20000,
                    step=100,
                ).classes("w-full")

                ui.label("OCR").classes("text-xl page-title")

                ocr_language = ui.input(
                    "OCR Sprache",
                    value=config["ocr"]["language"],
                ).classes("w-full")

                log_level = ui.select(
                    ["DEBUG", "INFO", "WARNING", "ERROR"],
                    value=config["logging"]["level"],
                    label="Log Level",
                ).classes("w-full")

            with ui.column().classes("gap-3 w-96"):
                ui.label("Pfade").classes("text-xl page-title")
                ui.label(
                    "Änderungen wirken erst nach einem Neustart der Anwendung."
                ).classes("text-xs muted")

                inbox_path = ui.input(
                    "Inbox", value=config["paths"]["inbox"]
                ).classes("w-full")
                archive_path = ui.input(
                    "Archiv", value=config["paths"]["archive"]
                ).classes("w-full")
                exports_path = ui.input(
                    "Export", value=config["paths"]["exports"]
                ).classes("w-full")
                database_path = ui.input(
                    "Datenbank", value=config["database"]["path"]
                ).classes("w-full")

        def save():
            config["classifier"]["model"] = model.value
            config["classifier"]["temperature"] = float(temperature.value)
            config["classifier"]["max_input_chars"] = int(max_input_chars.value)
            config["ocr"]["language"] = ocr_language.value
            config["logging"]["level"] = log_level.value
            config["paths"]["inbox"] = inbox_path.value
            config["paths"]["archive"] = archive_path.value
            config["paths"]["exports"] = exports_path.value
            config["database"]["path"] = database_path.value
            save_config(config)
            ui.notify("Einstellungen gespeichert.")

        ui.button("💾 Speichern", on_click=save).props("color=primary unelevated")

        # ------------------------------------------------------------
        # Log-Ansicht
        # ------------------------------------------------------------
        ui.label("📜 Log").classes("text-xl page-title")

        log_state = {"level": "ALLE"}

        @ui.refreshable
        def log_area():
            lines = read_log_tail(max_lines=200, level=log_state["level"])

            if not lines:
                ui.label("Keine Log-Einträge gefunden.").classes("muted")
                return

            ui.label(f"{len(lines)} Zeilen (neueste zuerst)").classes(
                "text-xs muted"
            )
            ui.code("\n".join(lines), language=None).classes("w-full").style(
                "max-height: 40vh; overflow: auto;"
            )

        with ui.row().classes("items-center gap-4"):
            ui.select(
                LOG_LEVELS,
                value="ALLE",
                label="Level",
                on_change=lambda event: (
                    log_state.update(level=event.value),
                    log_area.refresh(),
                ),
            ).classes("w-36")

            ui.button("🔄 Aktualisieren", on_click=log_area.refresh).props("flat")

        with card("w-full"):
            log_area()

        # ------------------------------------------------------------
        # Gefahrenzone
        # ------------------------------------------------------------
        ui.label("🚨 Gefahrenzone").classes("text-xl page-title text-red-600")
        ui.label(
            "Löscht alle archivierten Dokumente unwiderruflich und "
            "initialisiert die Datenbank neu."
        ).classes("muted")

        with ui.dialog() as reset_dialog, ui.card():
            ui.label("Wirklich alles löschen?").classes("font-bold")
            ui.label(
                "Alle archivierten Dokumente werden endgültig entfernt und "
                "die Datenbank wird neu initialisiert. Dieser Schritt kann "
                "nicht rückgängig gemacht werden."
            )

            confirm_input = ui.input('Zum Bestätigen "LÖSCHEN" eingeben').classes(
                "w-full"
            )

            def do_reset():
                if confirm_input.value.strip().upper() != "LÖSCHEN":
                    ui.notify(
                        'Bitte "LÖSCHEN" eingeben, um zu bestätigen.',
                        type="warning",
                    )
                    return

                removed = reset_database_and_archive()
                reset_dialog.close()
                ui.notify(
                    f"Datenbank zurückgesetzt. {removed} Archiv-Einträge entfernt.",
                    type="positive",
                )

            with ui.row().classes("justify-end w-full"):
                ui.button("Abbrechen", on_click=reset_dialog.close).props("flat")
                ui.button("Endgültig löschen", on_click=do_reset).props(
                    "color=negative"
                )

        ui.button(
            "🗑 Datenbank & Archiv löschen",
            on_click=reset_dialog.open,
        ).props("color=negative outline")

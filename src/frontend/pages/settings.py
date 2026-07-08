from nicegui import ui

from src.core.config import load_config, save_config
from src.database.reset_database import reset_database_and_archive
from src.frontend.layout import page_layout
from src.services.log_service import LOG_LEVELS, read_log_tail

MODEL_OPTIONS = ["gemma3:4b", "qwen3:1.7b", "llama3"]


@ui.page("/einstellungen")
def settings_page():
    config = load_config()

    with page_layout("Einstellungen"):
        ui.label("⚙ Einstellungen").classes("text-2xl font-bold")

        # ------------------------------------------------------------
        # Konfiguration
        # ------------------------------------------------------------
        current_model = config["classifier"]["model"]
        model_options = (
            MODEL_OPTIONS if current_model in MODEL_OPTIONS else [current_model, *MODEL_OPTIONS]
        )

        with ui.row().classes("gap-8 w-full items-start"):
            with ui.column().classes("gap-3 w-96"):
                ui.label("Klassifikation").classes("text-xl font-bold")

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

                ui.label("OCR").classes("text-xl font-bold")

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
                ui.label("Pfade").classes("text-xl font-bold")
                ui.label(
                    "Änderungen wirken erst nach einem Neustart der Anwendung."
                ).classes("text-xs text-gray-500")

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

        ui.button("💾 Speichern", on_click=save).props("color=primary")

        # ------------------------------------------------------------
        # Log-Ansicht
        # ------------------------------------------------------------
        ui.separator()
        ui.label("📜 Log").classes("text-xl font-bold")

        log_state = {"level": "ALLE"}

        @ui.refreshable
        def log_area():
            lines = read_log_tail(max_lines=200, level=log_state["level"])

            if not lines:
                ui.label("Keine Log-Einträge gefunden.").classes("text-gray-500")
                return

            ui.label(f"{len(lines)} Zeilen (neueste zuerst)").classes(
                "text-xs text-gray-500"
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

        log_area()

        # ------------------------------------------------------------
        # Gefahrenzone
        # ------------------------------------------------------------
        ui.separator()
        ui.label("🚨 Gefahrenzone").classes("text-xl font-bold text-red-600")
        ui.label(
            "Löscht alle archivierten Dokumente unwiderruflich und "
            "initialisiert die Datenbank neu."
        ).classes("text-gray-500")

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

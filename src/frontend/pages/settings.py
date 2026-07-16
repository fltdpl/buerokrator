from nicegui import app, ui

from src.core.config import load_config, save_config
from src.database.reset_database import reset_database_and_archive
from src.frontend.layout import card, page_layout
from src.frontend.pages.trash import render_trash
from src.services.backup_service import run_backup
from src.services.dependency_service import collect_dependency_status
from src.services.log_service import LOG_LEVELS, read_log_tail
from src.services.model_service import list_installed_models


def _backup_target(config):
    return config.get("backup", {}).get("target", "./backups")


@ui.page("/einstellungen")
def settings_page():
    config = load_config()

    with page_layout("Einstellungen"):
        ui.label("Einstellungen").classes("text-3xl page-title")

        with ui.tabs().classes("w-full") as tabs:
            tab_config = ui.tab("Konfiguration", icon="tune")
            tab_trash = ui.tab("Papierkorb", icon="delete_outline")
            tab_backup = ui.tab("Backup", icon="save")
            tab_database = ui.tab("Datenbank", icon="storage")
            tab_log = ui.tab("Log", icon="article")

        with ui.tab_panels(tabs, value=tab_config).classes("w-full"):
            with ui.tab_panel(tab_config):
                _render_config(config)

            with ui.tab_panel(tab_trash):
                render_trash()

            with ui.tab_panel(tab_backup):
                _render_backup(config)

            with ui.tab_panel(tab_database):
                _render_database_danger_zone()

            with ui.tab_panel(tab_log):
                _render_log()


def _render_dependency_status(config):
    """Zeigt an, ob die externen Abhängigkeiten verfügbar sind."""

    @ui.refreshable
    def status_list():
        for status in collect_dependency_status(config):
            with ui.row().classes("items-center gap-3 w-full no-wrap"):
                if status["ok"]:
                    ui.icon("check_circle").classes("text-green-600")

                else:
                    ui.icon("cancel").classes("text-red-600")

                ui.label(status["name"]).classes("w-40")
                ui.label(status["detail"]).classes("text-sm muted")

    with card("w-full gap-2"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label("Systemstatus").classes("text-xl page-title")

            with ui.row().classes("gap-1 items-center"):
                ui.button(
                    "Einrichtungsassistent",
                    on_click=lambda: ui.navigate.to("/einrichtung"),
                ).props("flat dense no-caps")
                ui.button(
                    icon="refresh", on_click=lambda: status_list.refresh()
                ).props("flat dense round")

        status_list()


def _render_config(config):
    _render_dependency_status(config)

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
            backup_path = ui.input(
                "Backup-Ziel", value=_backup_target(config)
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
        config.setdefault("backup", {})["target"] = backup_path.value
        save_config(config)
        ui.notify("Einstellungen gespeichert.")

    ui.button("💾 Speichern", on_click=save).props("color=primary unelevated")

    _render_shutdown()


def _render_shutdown():
    """Beendet den Serverprozess sauber (wichtig im Browser-Modus des Bundles)."""

    async def confirm_shutdown():
        with ui.dialog() as dialog, ui.card():
            ui.label("Buerokrator beenden?").classes("text-lg page-title")
            ui.label(
                "Der Hintergrundprozess wird gestoppt; dieser Browser-Tab "
                "kann danach geschlossen werden."
            ).classes("muted")
            with ui.row().classes("justify-end w-full"):
                ui.button("Abbrechen", on_click=lambda: dialog.submit(False)).props(
                    "flat no-caps"
                )
                ui.button("Beenden", on_click=lambda: dialog.submit(True)).props(
                    "color=negative unelevated no-caps"
                )

        if await dialog:
            ui.notify("Buerokrator wird beendet …")
            app.shutdown()

    with card("w-full gap-2"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label("Anwendung").classes("text-xl page-title")
            ui.button("Beenden", icon="power_settings_new", on_click=confirm_shutdown).props(
                "flat dense no-caps color=negative"
            )


def _render_backup(config):
    ui.label(
        "Sichert Datenbank und Archivordner als eine ZIP-Datei am unten "
        "genannten Ort. Das Ziel lässt sich unter Konfiguration → Pfade ändern."
    ).classes("muted")

    with card("w-full gap-3"):
        ui.label(f"Backup-Ziel: {_backup_target(config)}").classes("text-sm muted")

        def do_backup():
            try:
                zip_path = run_backup()

            except Exception as error:
                ui.notify(f"Backup fehlgeschlagen: {error}", type="negative")
                return

            size_mb = zip_path.stat().st_size / 1024 / 1024
            ui.notify(
                f"Backup erstellt: {zip_path} ({size_mb:.1f} MB)",
                type="positive",
            )

        ui.button("💾 Backup jetzt erstellen", on_click=do_backup).props(
            "color=primary unelevated"
        )


def _render_database_danger_zone():
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


def _render_log():
    log_state = {"level": "ALLE"}

    @ui.refreshable
    def log_area():
        lines = read_log_tail(max_lines=200, level=log_state["level"])

        if not lines:
            ui.label("Keine Log-Einträge gefunden.").classes("muted")
            return

        ui.label(f"{len(lines)} Zeilen (neueste zuerst)").classes("text-xs muted")
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

"""Einrichtungsassistent (First-Run): Systemcheck → Speicherorte → fertig.

Erscheint automatisch nur bei frischen Instanzen (siehe
setup_service.needs_setup), ist aber jederzeit unter /einrichtung erreichbar
(z. B. aus dem Systemstatus in den Einstellungen).
"""

from nicegui import ui

from src.core.config import load_config, save_config
from src.frontend.layout import card, page_layout
from src.services.setup_service import (
    all_checks_ok,
    complete_setup,
    setup_checks,
)


def _render_check(check):
    with ui.row().classes("items-center gap-3 w-full no-wrap"):
        if check["ok"]:
            ui.icon("check_circle").classes("text-green-600")

        else:
            ui.icon("cancel").classes("text-red-600")

        ui.label(check["name"]).classes("w-48")

        with ui.column().classes("gap-0"):
            ui.label(check["detail"]).classes("text-sm muted")

            if not check["ok"] and check["hint"]:
                ui.label(f"Installation: {check['hint']}").classes(
                    "text-sm font-mono"
                )


@ui.page("/einrichtung")
def setup_page():
    config = load_config()

    with page_layout("Einrichtung"):
        ui.label("Einrichtung").classes("text-3xl page-title")
        ui.label(
            "Ein paar Schritte, bis Buerokrator einsatzbereit ist."
        ).classes("muted")

        with card("w-full"), ui.stepper().props("vertical flat").classes(
            "w-full"
        ) as stepper:
            # ---------------------------------------------------------- 1
            with ui.step("Systemcheck"):
                ui.label(
                    "Buerokrator arbeitet komplett lokal und braucht dafür"
                    " diese Werkzeuge:"
                )

                @ui.refreshable
                def checks_area():
                    checks = setup_checks(config)

                    for check in checks:
                        _render_check(check)

                    if not all_checks_ok(checks):
                        ui.label(
                            "Fehlendes lässt sich auch später nachholen —"
                            " ohne Ollama/Modell funktioniert aber kein"
                            " Import."
                        ).classes("text-sm text-orange-700")

                checks_area()

                with ui.stepper_navigation():
                    ui.button("Weiter", on_click=stepper.next).props(
                        "color=primary unelevated"
                    )
                    ui.button(
                        "Erneut prüfen", on_click=checks_area.refresh
                    ).props("flat")

            # ---------------------------------------------------------- 2
            with ui.step("Speicherorte"):
                ui.label(
                    "Wo sollen neue Dokumente (Inbox) und das Archiv"
                    " liegen? Die Vorgaben sind sinnvoll — nur ändern,"
                    " wenn du einen bestimmten Ort willst."
                )

                inbox_input = ui.input(
                    "Inbox", value=config["paths"]["inbox"]
                ).classes("w-96")
                archive_input = ui.input(
                    "Archiv", value=config["paths"]["archive"]
                ).classes("w-96")

                def save_paths():
                    config["paths"]["inbox"] = inbox_input.value
                    config["paths"]["archive"] = archive_input.value
                    save_config(config)
                    stepper.next()

                with ui.stepper_navigation():
                    ui.button("Weiter", on_click=save_paths).props(
                        "color=primary unelevated"
                    )
                    ui.button("Zurück", on_click=stepper.previous).props("flat")

            # ---------------------------------------------------------- 3
            with ui.step("Gut zu wissen"):
                ui.markdown(
                    "- **Verarbeitung braucht Zeit**: Die Analyse läuft"
                    " lokal über ein Sprachmodell. Ohne Grafikkarte kann"
                    " ein Dokument mehrere Minuten dauern — der Import"
                    " läuft im Hintergrund weiter.\n"
                    "- **Alles bleibt auf diesem Rechner**: keine Cloud,"
                    " keine Übertragung an Dritte.\n"
                    "- **Jedes Dokument wird geprüft**: Die automatische"
                    " Erkennung ist ein Vorschlag — freigegeben wird im"
                    " Prüf-Workflow."
                )

                def finish():
                    complete_setup()
                    ui.navigate.to("/")

                with ui.stepper_navigation():
                    ui.button("Fertig — los geht's", on_click=finish).props(
                        "color=primary unelevated"
                    )
                    ui.button("Zurück", on_click=stepper.previous).props("flat")

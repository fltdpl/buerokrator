from nicegui import run, ui

from src.core.config import load_config, save_config
from src.database.reset_database import reset_database_and_archive
from src.frontend.layout import card, page_layout
from src.frontend.pages.trash import render_trash
from src.frontend.theme import DANGER, DARK_ACTIVE, INK_MUTED
from src.services.profile_service import (
    MAX_PROFILE,
    absolute_data_paths,
    activate_profile,
    create_profile,
    list_profiles,
    missing_profiles,
    remove_profile,
    rename_profile,
)
from src.services.backup_service import list_backups, run_backup, run_restore
from src.services.dependency_service import collect_dependency_status
from src.services.log_service import LOG_LEVELS, read_log_tail
from src.organizer.issuer_normalizer import (
    ensure_aliases_file,
    load_aliases,
    parse_aliases_text,
)
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
            tab_profiles = ui.tab("Profile", icon="group")
            tab_aliases = ui.tab("Aliase", icon="label")
            tab_trash = ui.tab("Papierkorb", icon="delete_outline")
            tab_backup = ui.tab("Backup", icon="save")
            tab_database = ui.tab("Datenbank", icon="storage")
            tab_log = ui.tab("Log", icon="article")

        with ui.tab_panels(tabs, value=tab_config).classes("w-full"):
            with ui.tab_panel(tab_config):
                _render_config(config)

            with ui.tab_panel(tab_profiles):
                _render_profiles()

            with ui.tab_panel(tab_aliases):
                _render_issuer_aliases()

            with ui.tab_panel(tab_trash):
                render_trash()

            with ui.tab_panel(tab_backup):
                _render_backup(config)

            with ui.tab_panel(tab_database):
                _render_database_danger_zone()

            with ui.tab_panel(tab_log):
                _render_log()


@ui.refreshable
def _render_profiles():
    """Personen des Haushalts: umbenennen, wechseln, hinzufügen, entfernen.

    Jede Person hat einen eigenen, vollständig getrennten Bestand. Solange
    es nur eine gibt, ist das nirgends sonst in der App sichtbar (ADR 015).
    """
    ui.label("Personen im Haushalt").classes("text-xl page-title")

    absolut = absolute_data_paths()

    if absolut:
        ui.label(
            "Achtung: "
            + ", ".join(absolut)
            + " ist als absoluter Pfad eingetragen. Dieses Verzeichnis wäre "
            "für alle Personen dasselbe — die Trennung der Bestände greift "
            "dort nicht. Bitte auf einen relativen Pfad umstellen."
        ).classes("text-sm").style(f"color: {DANGER}")

    profile = list_profiles()
    fehlend = missing_profiles()

    for eintrag in profile:
        with ui.row().classes("items-center gap-3 w-full"):
            ui.icon("person").classes("text-lg").style(
                f"color: {DARK_ACTIVE if eintrag['active'] else INK_MUTED}"
            )

            name = ui.input(value=eintrag["name"]).classes("w-64").props("dense")

            def umbenennen(_=None, kennung=eintrag["id"], feld=None):
                try:
                    rename_profile(kennung, feld.value)

                except RuntimeError as error:
                    ui.notify(str(error), type="warning")
                    return

                ui.notify("Name gespeichert.", type="positive")
                _render_profiles.refresh()

            name.on(
                "blur",
                lambda _=None, kennung=eintrag["id"], feld=name: umbenennen(
                    kennung=kennung, feld=feld
                ),
            )

            if eintrag["active"]:
                ui.label("geöffnet").classes("text-sm").style(f"color: {DARK_ACTIVE}")

            else:
                ui.button(
                    "Öffnen",
                    on_click=lambda _=None, kennung=eintrag["id"]: _wechseln(kennung),
                ).props("flat dense")

                ui.button(
                    "Aus der Liste nehmen",
                    on_click=lambda _=None, kennung=eintrag["id"]: _entfernen(kennung),
                ).props("flat dense")

            if eintrag["id"] in fehlend:
                ui.label("Ordner nicht gefunden").classes("text-sm").style(
                    f"color: {DANGER}"
                )

    if len(profile) < MAX_PROFILE:
        ui.button(
            "Zweite Person hinzufügen" if len(profile) == 1
            else "Weitere Person hinzufügen",
            on_click=_hinzufuegen,
        ).props("color=primary unelevated" if len(profile) == 1 else "flat")

        if len(profile) == 1:
            ui.label(
                "Die zweite Person bekommt einen eigenen, getrennten "
                "Bestand: eigene Dokumente, eigenes Archiv, eigene "
                "Aussteller-Aliase — und eigene Steuersummen. Die "
                "Einstellungen auf dieser Seite gelten weiterhin für alle."
            ).classes("text-sm muted")

    else:
        ui.label(
            f"Mehr als {MAX_PROFILE} Personen sind nicht vorgesehen — diese "
            "Ablage ist für einen Haushalt gedacht."
        ).classes("text-sm muted")

    ui.label(
        "Entfernen nimmt eine Person nur aus dieser Liste. Der Ordner mit "
        "ihren Dokumenten bleibt liegen und lässt sich jederzeit wieder "
        "eintragen."
    ).classes("text-sm muted")


def _wechseln(profile_id):
    try:
        activate_profile(profile_id)

    except RuntimeError as error:
        ui.notify(str(error), type="warning")
        return

    ui.navigate.to("/")


def _entfernen(profile_id):
    try:
        verzeichnis = remove_profile(profile_id)

    except RuntimeError as error:
        ui.notify(str(error), type="warning")
        return

    ui.notify(
        f"Aus der Liste genommen. Die Dokumente liegen weiterhin unter "
        f"{verzeichnis}.",
        type="positive",
        timeout=0,
        close_button=True,
    )
    _render_profiles.refresh()


def _hinzufuegen():
    try:
        create_profile()

    except RuntimeError as error:
        ui.notify(str(error), type="warning")
        return

    _render_profiles.refresh()


def _render_dependency_status(config):
    """Zeigt an, ob die externen Abhängigkeiten verfügbar sind."""

    @ui.refreshable
    def status_list():
        for status in collect_dependency_status(config):
            with ui.row().classes("items-center gap-3 w-full no-wrap"):
                if status["ok"]:
                    ui.icon("check_circle").classes("text-green-600")

                elif not status.get("required", True):
                    # Optional (Ollama): Warnung statt Fehler.
                    ui.icon("warning").classes("text-orange-600")

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


def _render_issuer_aliases():
    """Editor für die Aussteller-Alias-Datei (nutzerpflegbares YAML).

    Bewusst ein Text-Editor statt Formular: die Datei bleibt die eine
    Quelle (extern editierbar, Kommentare bleiben erhalten); gespeichert
    wird nur, was die Validierung besteht.
    """
    with card("w-full gap-2"):
        ui.label("Aussteller-Aliase").classes("text-xl page-title")
        ui.label(
            "Vereinheitlicht Schreibweisen desselben Ausstellers schon beim "
            "Import (Dateiname und gespeicherter Aussteller). Aufbau: "
            "kanonischer Name, darunter die Schreibweisen als Liste; ein "
            "Stern am Ende matcht als Präfix. Änderungen wirken ohne "
            "Neustart. Bestandsdokumente vereinheitlicht die Bulk-Aktion "
            "in der Dokumentenliste."
        ).classes("text-sm muted")

        path = ensure_aliases_file()
        ui.label(f"Datei: {path} (auch extern editierbar)").classes(
            "text-xs muted"
        )

        editor = ui.textarea(
            value=path.read_text(encoding="utf-8")
        ).classes("w-full font-mono").props("outlined input-style=height:22rem")

        @ui.refreshable
        def summary():
            exact, prefixes = load_aliases()
            ui.label(
                f"Aktiv: {len(exact)} Schreibweise(n), "
                f"{len(prefixes)} Präfix(e)."
            ).classes("text-sm muted")

        def save_aliases():
            try:
                exact, prefixes = parse_aliases_text(editor.value)

            except ValueError as error:
                ui.notify(f"Nicht gespeichert — {error}", type="negative")
                return

            path.write_text(editor.value, encoding="utf-8")
            ui.notify(
                f"Gespeichert: {len(exact)} Schreibweise(n), "
                f"{len(prefixes)} Präfix(e)."
            )
            summary.refresh()

        def reload():
            editor.value = path.read_text(encoding="utf-8")
            ui.notify("Neu geladen.")
            summary.refresh()

        with ui.row().classes("gap-2 items-center"):
            ui.button("💾 Speichern", on_click=save_aliases).props(
                "color=primary unelevated"
            )
            ui.button("Neu laden", on_click=reload).props("flat no-caps")

        summary()


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

    _render_restore(config)


def _render_restore(config):
    """Backup-ZIP aus dem Zielordner auswählen und wiederherstellen."""

    @ui.refreshable
    def restore_area():
        backups = list_backups(_backup_target(config))

        if not backups:
            ui.label("Keine Backups im Zielordner gefunden.").classes("muted")
            return

        options = {
            entry["path"]: f"{entry['name']} ({entry['size_mb']:.1f} MB)"
            for entry in backups
        }
        selected = ui.select(
            options,
            value=backups[0]["path"],
            label="Backup auswählen",
        ).classes("w-full")

        async def confirm_restore():
            with ui.dialog() as dialog, ui.card():
                ui.label("Backup wiederherstellen?").classes("text-lg page-title")
                ui.label(
                    "Datenbank und Archiv werden durch den Stand aus der "
                    "Sicherung ersetzt. Der aktuelle Stand wird nicht "
                    "gelöscht, sondern daneben abgelegt "
                    "(pre_restore_… / …_vor_wiederherstellung_…)."
                ).classes("muted")
                with ui.row().classes("justify-end w-full"):
                    ui.button(
                        "Abbrechen", on_click=lambda: dialog.submit(False)
                    ).props("flat no-caps")
                    ui.button(
                        "Wiederherstellen", on_click=lambda: dialog.submit(True)
                    ).props("color=negative unelevated no-caps")

            if not await dialog:
                return

            try:
                result = await run.io_bound(run_restore, selected.value)

            except Exception as error:
                ui.notify(
                    f"Wiederherstellung fehlgeschlagen: {error}", type="negative"
                )
                return

            ui.notify(
                f"Backup wiederhergestellt ({result['archive_files']} "
                "Archivdateien). Seite neu laden, um den Stand zu sehen.",
                type="positive",
            )

        with ui.row().classes("gap-2 items-center"):
            ui.button("♻️ Wiederherstellen", on_click=confirm_restore).props(
                "color=negative unelevated no-caps"
            )
            ui.button(icon="refresh", on_click=restore_area.refresh).props(
                "flat dense round"
            )

    with card("w-full gap-3"):
        ui.label("Wiederherstellen").classes("text-xl page-title")
        ui.label(
            "Stellt Datenbank und Archiv aus einer Backup-ZIP wieder her. "
            "Der aktuelle Stand wird zuvor beiseitegelegt, nichts wird "
            "gelöscht."
        ).classes("text-sm muted")

        restore_area()


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

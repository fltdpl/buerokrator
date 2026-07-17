"""Gemeinsames Seitenlayout (Seitenleiste + Kopf) für alle NiceGUI-Seiten."""

import asyncio
from contextlib import contextmanager

from nicegui import app, ui

from src import __version__
from src.frontend.theme import apply_theme

# (Label, Route, Material-Icon)
NAV_ITEMS = [
    ("Dashboard", "/", "dashboard"),
    ("Dokumente", "/dokumente", "description"),
    ("Import", "/import", "file_upload"),
    ("Steuer", "/steuer", "account_balance"),
    ("Anleitung", "/anleitung", "help_outline"),
    ("Einstellungen", "/einstellungen", "settings"),
]


def format_euro(amount):
    return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _current_path():
    try:
        return ui.context.client.page.path

    except Exception:
        return ""


async def confirm_shutdown():
    """Beendet den Serverprozess nach Rückfrage (wichtig im Browser-Modus
    des Desktop-Pakets, wo es sonst kein sauberes Ende gibt)."""
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
        # Best effort: Browser dürfen window.close() ablehnen, wenn der Tab
        # nicht per Skript geöffnet wurde — dann bleibt der Tab einfach offen.
        # Kurze Wartezeit, damit das JS den Client vor dem Shutdown erreicht.
        ui.run_javascript("setTimeout(() => window.close(), 100)")
        await asyncio.sleep(0.5)
        app.shutdown()


def _is_active(route, path):
    """Aktiv ist der längste passende Präfix — /dokumente/{id} markiert
    „Dokumente", ohne dass „/" (Dashboard) mitleuchtet."""
    if route == "/":
        return path == "/"

    return path.startswith(route)


@contextmanager
def page_layout(title):
    """Seitenleiste + Kopfzeile; der Seiteninhalt entsteht im with-Block."""
    apply_theme()
    ui.page_title(f"{title} – Buerokrator")

    path = _current_path()

    # Breiter als die üblichen 240px: "BUEROKRATOR" in Überschriftengröße
    # braucht den Platz, sonst bricht die Wortmarke um.
    with ui.left_drawer(fixed=True).classes("sidebar p-0").props("width=264 bordered"):
        ui.label("BUEROKRATOR").classes("text-3xl page-title brand")

        for label, route, icon in NAV_ITEMS:
            active = " active" if _is_active(route, path) else ""

            with ui.link(target=route).classes(f"nav-item{active}"):
                ui.icon(icon).classes("text-lg")
                ui.label(label).classes("text-sm")

        with ui.row().classes("nav-item cursor-pointer").on("click", confirm_shutdown):
            ui.icon("power_settings_new").classes("text-lg")
            ui.label("Beenden").classes("text-sm")

        ui.label(f"v{__version__}").classes("text-xs muted p-4")

    with ui.column().classes("w-full max-w-7xl mx-auto p-6 gap-4"):
        yield


@contextmanager
def card(classes=""):
    """Inhaltskarte im Stil der Vorlage."""
    with ui.column().classes(f"paper-card p-4 gap-2 {classes}"):
        yield

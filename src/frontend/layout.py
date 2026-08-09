"""Gemeinsames Seitenlayout (Seitenleiste + Kopf) für alle NiceGUI-Seiten."""

import asyncio
from contextlib import contextmanager

from nicegui import app, ui

from src import __version__
from src.frontend.theme import apply_theme
from src.services.profile_service import activate_profile, list_profiles

# (Label, Route, Material-Icon)
NAV_ITEMS = [
    ("Dashboard", "/", "dashboard"),
    ("Dokumente", "/dokumente", "description"),
    ("Import", "/import", "file_upload"),
    ("Analyse", "/analyse", "query_stats"),
    ("Anleitung", "/anleitung", "help_outline"),
    ("Einstellungen", "/einstellungen", "settings"),
]


def umzug_noetig() -> bool:
    """Weiche für JEDE Seite: ein Altbestand gehört zuerst umgezogen.

    Bewusst nicht nur auf dem Dashboard. Jede Seite, die die Datenbank
    öffnet, legt sonst im (noch leeren) Profil eine an — danach lehnte der
    Umzug ab, weil `profiles/` bereits existiert, und der Nutzer las eine
    Aufforderung, etwas zu löschen, das die App selbst angelegt hatte.
    Gefunden im Smoke-Test des fertigen Pakets: ein Klick auf „Dokumente"
    vor dem Umzug genügte.
    """
    from src.services.profile_port import legacy_bestand_gefunden

    if not legacy_bestand_gefunden():
        return False

    ui.navigate.to("/umzug")

    return True


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


def _switch_profile(profile_id):
    """Profil wechseln und die Seite neu aufbauen lassen.

    Der Neuaufbau ist nötig, nicht kosmetisch: Seiten halten modulglobalen
    Zustand (z. B. den Suchfilter der Dokumentenliste), der zum vorherigen
    Bestand gehört.
    """
    try:
        activate_profile(profile_id)

    except RuntimeError as error:
        ui.notify(str(error), type="warning")
        return

    ui.navigate.to("/")


def render_profile_switcher():
    """Aktives Profil samt Umschalter, direkt unter der Wortmarke.

    Der Name steht **immer** da, auch bei einer einzigen Person: es ist die
    Antwort auf „wessen Unterlagen sehe ich hier gerade", und die soll man
    nicht suchen müssen. Der Umschalter erscheint erst, wenn es überhaupt
    etwas zu wechseln gibt — der teuerste Bedienfehler dieses Features wäre
    ein Stapel im falschen Bestand.

    Oben statt unten und in derselben Flucht wie die Navigationspunkte: das
    Profil gehört zur Identität der Ansicht, nicht zu den Fußnoten. Eine
    eigene Kopfzeile wäre die Alternative gewesen — sie hätte auf jeder Seite
    vertikalen Platz gekostet, am teuersten in der Dokumentansicht.
    """
    profile = list_profiles()
    aktiv = next((p for p in profile if p["active"]), profile[0])

    # Name und Umschalter in EINEM Block ohne Zwischenraum: die Drawer-Spalte
    # setzt zwischen ihren Kindern eine Lücke, die den Knopf sonst vom Namen
    # abrücken würde, zu dem er gehört.
    with ui.column().classes("w-full gap-0"):
        with ui.column().classes("profile-block gap-0"):
            ui.label("Nutzerprofil").classes("text-xs profile-role")

            # Umschalter NEBEN dem Namen statt darunter: als eigene Zeile in
            # der Flucht der Navigationspunkte las er sich wie ein siebter
            # Menüeintrag und machte den Kopf der Leiste unruhig. Klein und
            # direkt am Namen gehört er sichtbar zu ihm.
            with ui.row().classes("items-center gap-2 no-wrap"):
                ui.label(aktiv["name"]).classes("text-sm")

                if len(profile) > 1:
                    with ui.row().classes(
                        "items-center gap-1 no-wrap cursor-pointer profile-switch"
                    ).mark("profil-wechseln"):
                        ui.icon("swap_horiz").classes("text-sm")
                        ui.label("wechseln").classes("text-xs")
                        ui.tooltip("Benutzer wechseln")

                        with ui.menu():
                            for eintrag in profile:
                                if eintrag["active"]:
                                    continue

                                # Marker, weil eine Textsuche im Test die
                                # innere ItemSection trifft und nicht den
                                # klickbaren Eintrag.
                                ui.menu_item(
                                    f"Zu {eintrag['name']} wechseln",
                                    lambda _=None, kennung=eintrag[
                                        "id"
                                    ]: _switch_profile(kennung),
                                ).mark(f"profil-wechsel-{eintrag['id']}")

    ui.element("div").classes("sidebar-divider")


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

        render_profile_switcher()

        for label, route, icon in NAV_ITEMS:
            active = " active" if _is_active(route, path) else ""

            with ui.link(target=route).classes(f"nav-item{active}"):
                ui.icon(icon).classes("text-lg")
                ui.label(label).classes("text-sm")

        # Trennlinie über „Beenden": es verlässt die App, statt in ihr zu
        # navigieren — und soll deshalb nicht wie der nächste Menüpunkt
        # aussehen.
        ui.element("div").classes("sidebar-divider")

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

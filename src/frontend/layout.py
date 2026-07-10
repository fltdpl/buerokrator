"""Gemeinsames Seitenlayout (Seitenleiste + Kopf) für alle NiceGUI-Seiten."""

from contextlib import contextmanager

from nicegui import ui

from src.frontend.theme import apply_theme

# (Label, Route, Material-Icon)
NAV_ITEMS = [
    ("Dashboard", "/", "dashboard"),
    ("Dokumente", "/dokumente", "description"),
    ("Import", "/import", "file_upload"),
    ("Steuer", "/steuer", "account_balance"),
    ("Einstellungen", "/einstellungen", "settings"),
]


def format_euro(amount):
    return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _current_path():
    try:
        return ui.context.client.page.path

    except Exception:
        return ""


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

    with ui.column().classes("w-full max-w-7xl mx-auto p-6 gap-4"):
        yield


@contextmanager
def card(classes=""):
    """Inhaltskarte im Stil der Vorlage."""
    with ui.column().classes(f"paper-card p-4 gap-2 {classes}"):
        yield

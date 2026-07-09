"""Gemeinsames Seitenlayout (Header + Navigation) für alle NiceGUI-Seiten."""

from contextlib import contextmanager

from nicegui import ui

NAV_ITEMS = [
    ("Dashboard", "/"),
    ("Dokumente", "/dokumente"),
    ("Import", "/import"),
    ("Steuer", "/steuer"),
    ("Papierkorb", "/papierkorb"),
    ("Einstellungen", "/einstellungen"),
]


def format_euro(amount):
    return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


@contextmanager
def page_layout(title):
    """Header mit Navigation; der Seiteninhalt entsteht im with-Block."""
    with ui.header().classes("items-center gap-6 px-6"):
        ui.label("📄 Buerokrator").classes("text-lg font-bold")

        for label, target in NAV_ITEMS:
            ui.link(label, target).classes("text-white no-underline hover:underline")

    ui.page_title(f"{title} – Buerokrator")

    with ui.column().classes("w-full max-w-7xl mx-auto p-4 gap-4"):
        yield

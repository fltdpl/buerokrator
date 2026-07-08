"""Platzhalter für Seiten, die erst in Phase 3 migriert werden."""

from nicegui import ui

from src.frontend.layout import page_layout


def _placeholder(title):
    with page_layout(title):
        ui.label(title).classes("text-2xl font-bold")
        ui.label(
            "Diese Seite ist noch nicht migriert — bitte vorerst die "
            "Streamlit-Oberfläche nutzen (streamlit run app.py, Port 8501)."
        ).classes("text-gray-500")


@ui.page("/import")
def import_page():
    _placeholder("📥 Import")


@ui.page("/steuer")
def tax_page():
    _placeholder("💰 Steuer")


@ui.page("/einstellungen")
def settings_page():
    _placeholder("⚙ Einstellungen")

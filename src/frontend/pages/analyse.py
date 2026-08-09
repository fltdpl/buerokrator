"""Analyse-Seite: Tabs „Steuer" (ELSTER-Zuordnung) und „Einkommen".

Das Gerüst (Route, Tabs) liegt hier; die Tab-Inhalte kommen als
Render-Funktionen aus pages/tax.py und pages/income.py.
"""

from nicegui import ui

from src.frontend.layout import page_layout, umzug_noetig
from src.frontend.pages.income import render_income_tab
from src.frontend.pages.tax import render_tax_tab


@ui.page("/analyse")
def analyse_page():
    # Altbestand zuerst umziehen (siehe layout.umzug_noetig).
    if umzug_noetig():
        return

    with page_layout("Analyse"):
        ui.label("📊 Analyse").classes("text-3xl page-title")

        with ui.tabs().classes("w-full") as tabs:
            tab_tax = ui.tab("Steuer", icon="account_balance")
            tab_income = ui.tab("Einkommen", icon="trending_up")

        with ui.tab_panels(tabs, value=tab_tax).classes("w-full"):
            with ui.tab_panel(tab_tax):
                render_tax_tab()

            with ui.tab_panel(tab_income):
                render_income_tab()


@ui.page("/steuer")
def steuer_redirect():
    """Alte Route: Lesezeichen und Gewohnheit weiter bedienen."""
    ui.navigate.to("/analyse")

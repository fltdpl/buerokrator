from nicegui import ui

from src.core.document_types import DOCUMENT_TYPE_LABELS
from src.database.list_documents import list_documents
from src.frontend.layout import format_euro, page_layout
from src.tax.elster_mapping import (
    EMPTY,
    INCOMPLETE,
    READY,
    build_elster_summary,
)
from src.tax.elster_mapping import UNCLEAR as POSITION_UNCLEAR
from src.tax.tax_summary import (
    available_tax_years,
    build_tax_summary,
    export_tax_summary_csv,
)

# Ampel je Anlagen-Position (siehe docs/05_Steuerlogik.md, Zielbild).
POSITION_STATUS = {
    READY: ("🟢", "übernahmefertig"),
    INCOMPLETE: ("🟡", "unvollständig — ungeprüfte Belege zählen nicht"),
    POSITION_UNCLEAR: ("❓", "unklar — bitte Belege klären"),
    EMPTY: ("⚪", "keine Belege"),
}

DEDUCTIBILITY_HINTS = {
    "deductible": "absetzbar",
    "not_deductible": "nicht absetzbar",
    "unclear": "❓ Art unklar",
}


def _reference_list(title, references, note=""):
    """Beleg-Liste einer Position (Herleitung) mit Links in die Detailansicht."""
    if not references:
        return

    suffix = f" · {note}" if note else ""
    ui.label(f"{title}{suffix}").classes("text-xs muted")

    for ref in references:
        amount = format_euro(ref["amount"]) if ref["amount"] is not None else "—"
        ui.link(
            f"• {ref['issuer'] or ref['filename']} · {amount}",
            f"/dokumente/{ref['id']}",
        ).classes("text-sm")


def _position_row(position):
    """Eine Anlagen-Position: Ampel + Betrag, aufklappbare Herleitung."""
    icon, status_text = POSITION_STATUS[position["status"]]

    if position["status"] == EMPTY:
        ui.label(f"{icon} {position['label']} — keine Belege").classes(
            "text-xs muted"
        )
        return

    header = f"{icon} {position['label']}  —  {format_euro(position['amount'])}"

    with ui.expansion(header).classes("w-full"):
        ui.label(status_text).classes("text-xs muted")

        if position["hint"]:
            ui.label(f"⚠️ {position['hint']}").classes("text-sm text-amber-700")

        _reference_list("Belege (gezählt)", position["documents"])
        _reference_list(
            "Ungeprüft",
            position["pending"],
            note="zählen NICHT — erst prüfen",
        )
        _reference_list(
            "Geprüft, aber ohne diesen Wert",
            position["missing_value"],
            note="Feld nachtragen („Erneut prüfen“ oder von Hand)",
        )
        _reference_list(
            "Unklare Versicherungsart",
            position["unclear"],
            note="Art ergänzen, dann zählt der Betrag",
        )


def _anlagen_section(year):
    """Anlagen-Ansicht: die Werte, die in die Steuererklärung übernommen werden."""
    summary = build_elster_summary(year)

    for anlage in summary["anlagen"]:
        positions = anlage["positions"]
        filled = [p for p in positions if p["status"] != EMPTY]
        ready = sum(1 for p in filled if p["status"] == READY)

        with ui.card().classes("w-full"):
            with ui.row().classes("items-baseline gap-3"):
                ui.label(anlage["label"]).classes("text-xl page-title")

                if filled:
                    ui.label(
                        f"{ready} von {len(filled)} Positionen übernahmefertig"
                    ).classes("text-sm muted")

            if not filled:
                ui.label("Keine Belege für dieses Jahr.").classes("muted")

            for position in positions:
                _position_row(position)


@ui.page("/steuer")
def tax_page():
    documents = list_documents()
    years = available_tax_years(documents)

    with page_layout("Steuer"):
        ui.label("💰 Steuer").classes("text-3xl page-title")
        ui.label(
            "🚧 Die Steuer-Funktion ist noch im Aufbau — die Summen und die"
            " Absetzbarkeits-Einordnung sind eine erste Orientierung, kein"
            " geprüftes Ergebnis."
        ).classes("text-sm text-orange-700")

        if not years:
            ui.label("Noch keine archivierten Dokumente vorhanden.").classes(
                "muted"
            )
            return

        state = {"year": years[-1]}

        @ui.refreshable
        def summary_area():
            summary = build_tax_summary(state["year"], documents)
            totals = summary["totals"]

            ui.label(f"{totals['count']} Dokumente im Jahr {state['year']}").classes(
                "muted"
            )

            # Anlagen-Ansicht: nur geprüfte + steuerrelevante Belege zählen,
            # jede Summe ist über die Belegliste herleitbar.
            _anlagen_section(state["year"])

            ui.button(
                "📥 Jahres-Export (CSV)",
                on_click=lambda: ui.download(
                    export_tax_summary_csv(
                        build_tax_summary(state["year"], documents)
                    ).encode("utf-8"),
                    f"steuer_{state['year']}.csv",
                ),
            ).props("flat")

            ui.separator()
            ui.label("Alle Dokumente des Jahres (nach Lebensbereich)").classes(
                "text-xl page-title"
            )

            for category in summary["categories"]:
                hint = " · absetzbar (je nach Art)" if category["deductible"] else ""
                header = (
                    f"{category['label']}{hint}  —  {category['count']} Dok."
                    f"  ·  {format_euro(category['amount'])}"
                )

                with ui.expansion(header).classes("w-full"):
                    if category["verified_count"] < category["count"]:
                        ui.label(
                            f"🟡 {category['count'] - category['verified_count']} "
                            "ungeprüft · geprüfte Summe: "
                            f"{format_euro(category['verified_amount'])}"
                        ).classes("text-sm muted")

                    for document in category["documents"]:
                        status = "🟢" if document["verified"] else "🟡"
                        type_label = DOCUMENT_TYPE_LABELS.get(
                            document["document_type"], document["document_type"]
                        )
                        amount_text = (
                            format_euro(document["amount"])
                            if document["amount"] is not None
                            else "—"
                        )
                        deductibility = ""

                        if category["deductible"]:
                            deductibility = DEDUCTIBILITY_HINTS.get(
                                document["deductibility"], ""
                            )
                            deductibility = f" · {deductibility}" if deductibility else ""

                        # Nicht steuerrelevante Dokumente (z. B. redundante
                        # Monats-Gehaltsabrechnungen) sind gelistet, zählen aber
                        # nicht in die Summe — kenntlich machen.
                        relevance = (
                            "" if document.get("tax_relevant") else " · nicht steuerrelevant"
                        )

                        with ui.row().classes("gap-2 items-center"):
                            ui.label(
                                f"{status} {document['document_date'] or 'ohne Datum'}"
                            ).classes("text-sm w-36")
                            ui.link(
                                document["issuer"] or type_label,
                                f"/dokumente/{document['id']}",
                            )
                            ui.label(f"{amount_text}{deductibility}{relevance}").classes(
                                "text-sm font-bold"
                            )

        def change_year(year):
            state["year"] = year
            summary_area.refresh()

        ui.select(
            years,
            value=years[-1],
            label="Steuerjahr",
            on_change=lambda event: change_year(event.value),
        ).classes("w-36")

        summary_area()

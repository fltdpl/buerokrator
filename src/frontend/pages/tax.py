from nicegui import ui

from src.core.document_types import DOCUMENT_TYPE_LABELS
from src.database.list_documents import list_documents
from src.frontend.layout import format_euro, page_layout
from src.tax.tax_summary import (
    UNCLEAR,
    available_tax_years,
    build_tax_summary,
    export_tax_summary_csv,
)

DEDUCTIBILITY_HINTS = {
    "deductible": "absetzbar",
    "not_deductible": "nicht absetzbar",
    "unclear": "❓ Art unklar",
}


def _metric(label, value):
    with ui.card().classes("items-center min-w-48"):
        ui.label(value).classes("text-3xl page-title")
        ui.label(label).classes("text-sm muted")


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

            ungeprueft = (
                totals["deductible_amount"] - totals["deductible_verified_amount"]
            )

            with ui.row().classes("gap-4"):
                _metric(
                    "Absetzbar (geprüft)",
                    format_euro(totals["deductible_verified_amount"]),
                )
                _metric("davon ungeprüft", format_euro(ungeprueft))
                _metric("Erfasste Beträge gesamt", format_euro(totals["amount"]))
                _metric(
                    "Steuerrelevante Dokumente",
                    str(totals["tax_relevant_count"]),
                )

            if ungeprueft > 0:
                ui.label(
                    "⚠️ Es gibt ungeprüfte Beträge. Prüfe die betroffenen "
                    "Dokumente, bevor du die Summen für die Steuererklärung "
                    "verwendest."
                ).classes("text-amber-700")

            # Dokumente mit unklarer Absetzbarkeit direkt verlinken.
            unclear_documents = [
                document
                for category in summary["categories"]
                for document in category["documents"]
                if document["deductibility"] == UNCLEAR
                and document["amount"] is not None
            ]

            if unclear_documents:
                unclear_sum = totals["deductible_unclear_amount"]

                with ui.card().classes("w-full bg-blue-50"):
                    ui.label(
                        f"{format_euro(unclear_sum)} aus "
                        f"{len(unclear_documents)} Dokument(en) mit unklarer "
                        "Versicherungsart sind nicht in „Absetzbar“ enthalten. "
                        "Versicherungsart ergänzen, dann zählt der Betrag mit:"
                    )

                    for document in unclear_documents:
                        ui.link(
                            f"• {document['issuer'] or document['filename']}"
                            f" · {format_euro(document['amount'])}",
                            f"/dokumente/{document['id']}",
                        )

            ui.button(
                "📥 Jahres-Export (CSV)",
                on_click=lambda: ui.download(
                    export_tax_summary_csv(
                        build_tax_summary(state["year"], documents)
                    ).encode("utf-8"),
                    f"steuer_{state['year']}.csv",
                ),
            ).props("flat")

            capital = summary["capital_income"]

            if totals["income_tax"] or capital["count"]:
                ui.separator()
                ui.label("Weitere steuerrelevante Summen").classes(
                    "text-xl page-title"
                )

                with ui.row().classes("gap-4"):
                    _metric(
                        "Gezahlte Lohn-/Einkommensteuer",
                        format_euro(totals["income_tax"]),
                    )
                    _metric(
                        "Guthabenszinsen (Anlage KAP)",
                        format_euro(capital["interest"]),
                    )
                    _metric(
                        "Kapitalertragssteuer",
                        format_euro(capital["capital_gains_tax"]),
                    )

                if capital["count"]:
                    ui.label(
                        f"Kapitalerträge aus {capital['count']} "
                        "Steuerbescheinigung(en). Bauspar-Kontoauszüge zählen "
                        "nicht mit (Steuerbescheinigung ist maßgeblich)."
                    ).classes("text-xs muted")

            ui.separator()

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

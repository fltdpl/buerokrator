import streamlit as st

from src.core.document_types import DOCUMENT_TYPE_LABELS
from src.database.list_documents import list_documents
from src.tax.tax_summary import (
    available_tax_years,
    build_tax_summary,
    export_tax_summary_csv,
)


def _format_euro(amount):
    return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def render_tax_page():

    st.title("💰 Steuer")

    documents = list_documents()
    years = available_tax_years(documents)

    if not years:
        st.info("Noch keine archivierten Dokumente vorhanden.")

        return

    year = st.sidebar.selectbox(
        "Steuerjahr",
        years,
        index=len(years) - 1,
    )

    summary = build_tax_summary(year, documents)
    totals = summary["totals"]

    st.caption(f"{totals['count']} Dokumente im Jahr {year}")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Absetzbar (geprüft)",
        _format_euro(totals["deductible_verified_amount"]),
    )

    ungeprueft = totals["deductible_amount"] - totals["deductible_verified_amount"]

    col2.metric(
        "davon ungeprüft",
        _format_euro(ungeprueft),
    )

    col3.metric(
        "Erfasste Beträge gesamt",
        _format_euro(totals["amount"]),
    )

    if ungeprueft > 0:
        st.warning(
            "Es gibt ungeprüfte Beträge. Prüfe die betroffenen Dokumente, "
            "bevor du die Summen für die Steuererklärung verwendest."
        )

    st.download_button(
        "📥 Jahres-Export (CSV)",
        data=export_tax_summary_csv(summary),
        file_name=f"steuer_{year}.csv",
        mime="text/csv",
    )

    st.markdown("---")

    for category in summary["categories"]:
        deductible_hint = " · absetzbar" if category["deductible"] else ""

        header = (
            f"{category['label']}{deductible_hint}"
            f"  —  {category['count']} Dok."
            f"  ·  {_format_euro(category['amount'])}"
        )

        with st.expander(header):
            if category["verified_count"] < category["count"]:
                st.caption(
                    f"🟡 {category['count'] - category['verified_count']} ungeprüft"
                    f"  ·  geprüfte Summe: {_format_euro(category['verified_amount'])}"
                )

            for document in category["documents"]:
                status = "🟢" if document["verified"] else "🟡"
                type_label = DOCUMENT_TYPE_LABELS.get(
                    document["document_type"],
                    document["document_type"],
                )

                amount_text = (
                    _format_euro(document["amount"])
                    if document["amount"] is not None
                    else "—"
                )

                date_text = document["document_date"] or "ohne Datum"
                issuer_text = document["issuer"] or type_label

                st.write(
                    f"{status}  {date_text}  ·  {issuer_text}  ·  **{amount_text}**"
                )

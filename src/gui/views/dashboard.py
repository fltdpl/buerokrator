import streamlit as st

from src.core.document_types import INSURANCE, INVOICE, PENSION
from src.services.stats_service import get_dashboard_data


def render_dashboard(display_names):

    stats = get_dashboard_data()
    counts = stats["counts_by_type"]

    st.title("📄 Buerokrator")

    st.caption(f"{stats['total']} Dokumente archiviert")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Dokumente",
        stats["total"],
    )

    col2.metric(
        "Rechnungen",
        counts.get(INVOICE, 0),
    )

    col3.metric(
        "Versicherungen",
        counts.get(INSURANCE, 0),
    )

    col4.metric(
        "Vorsorge",
        counts.get(PENSION, 0),
    )

    # Aufgaben: die beiden Dinge, die tatsächlich Arbeit bedeuten —
    # Inbox importieren und ungeprüfte Dokumente durchsehen.
    if stats["unverified_count"] or stats["inbox_count"]:
        st.subheader("Aufgaben")

        task_col1, task_col2 = st.columns(2)

        with task_col1:
            if stats["unverified_count"]:
                if st.button(
                    f"🟡 {stats['unverified_count']} ungeprüfte Dokumente prüfen",
                    type="primary",
                    width="stretch",
                ):
                    # Direkt das erste ungeprüfte Dokument öffnen.
                    st.session_state["open_doc_id"] = stats["first_unverified_id"]
                    st.switch_page("pages/1_Dokumente.py")

        with task_col2:
            if stats["inbox_count"]:
                if st.button(
                    f"📥 {stats['inbox_count']} Datei(en) in der Inbox importieren",
                    width="stretch",
                ):
                    st.switch_page("pages/2_Import.py")

    else:
        st.success("Keine offenen Aufgaben — Inbox leer, alles geprüft.")

    st.subheader("Zuletzt archiviert")

    for row in stats["recent"]:
        st.write(f"{display_names.get(row[2], row[2])} - {row[1]}")

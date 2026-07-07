import streamlit as st

from src.core.document_types import INSURANCE, INVOICE, PENSION
from src.database.list_documents import get_next_unverified_id
from src.database.recent_documents import get_recent_documents
from src.database.statistics import get_verification_statistics
from src.processor.batch_import import find_inbox_documents


def render_dashboard(
    counts,
    total,
    display_names,
):

    st.title("📄 Buerokrator")

    st.caption(f"{total} Dokumente archiviert")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Dokumente",
        total,
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
    unverified_count = get_verification_statistics()[0]
    inbox_count = len(find_inbox_documents())

    if unverified_count or inbox_count:
        st.subheader("Aufgaben")

        task_col1, task_col2 = st.columns(2)

        with task_col1:
            if unverified_count:
                if st.button(
                    f"🟡 {unverified_count} ungeprüfte Dokumente prüfen",
                    type="primary",
                    width="stretch",
                ):
                    # Direkt das erste ungeprüfte Dokument öffnen.
                    st.session_state["open_doc_id"] = get_next_unverified_id()
                    st.switch_page("pages/1_Dokumente.py")

        with task_col2:
            if inbox_count:
                if st.button(
                    f"📥 {inbox_count} Datei(en) in der Inbox importieren",
                    width="stretch",
                ):
                    st.switch_page("pages/2_Import.py")

    else:
        st.success("Keine offenen Aufgaben — Inbox leer, alles geprüft.")

    st.subheader("Zuletzt archiviert")

    recent = get_recent_documents()

    for row in recent:
        st.write(f"{display_names.get(row[1], row[1])} - {row[0]}")

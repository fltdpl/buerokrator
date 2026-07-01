import streamlit as st

from src.core.document_types import DOCUMENT_TYPE_LABELS
from src.database.recent_documents import get_recent_documents
from src.database.statistics import get_statistics

DISPLAY_NAMES = {
    document_type: label
    for document_type, label in DOCUMENT_TYPE_LABELS.items()
}


def render_dashboard(
    counts,
    total,
    display_names,
):

    st.title("Buerokrator")

    st.caption(f"{total} Dokumente archiviert")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Dokumente",
        total,
    )

    col2.metric(
        "Rechnungen",
        counts.get("invoice", 0),
    )

    col3.metric(
        "Versicherungen",
        counts.get("insurance", 0),
    )

    col4.metric(
        "Vorsorge",
        counts.get("pension", 0),
    )

    st.subheader("Zuletzt archiviert")

    recent = get_recent_documents()

    for row in recent:
        st.write(f"{display_names.get(row[1], row[1])} - {row[0]}")


st.set_page_config(
    page_title="Buerokrator",
    layout="wide",
)

total, by_type = get_statistics()

counts = dict(by_type)

render_dashboard(
    counts,
    total,
    DISPLAY_NAMES,
)

import streamlit as st

from src.core.document_types import DOCUMENT_TYPE_LABELS
from src.database.list_documents import list_documents
from src.database.statistics import get_statistics
from src.gui.pdf_cache import cleanup_pdf_cache
from src.gui.views.dashboard import render_dashboard

DISPLAY_NAMES = dict(DOCUMENT_TYPE_LABELS)

st.set_page_config(
    page_title="Buerokrator",
    layout="wide",
)


@st.cache_resource
def _cleanup_pdf_cache_once():
    """Verwaiste Static-PDF-Kopien einmal pro App-Prozess aufräumen."""
    return cleanup_pdf_cache(row[0] for row in list_documents())


_cleanup_pdf_cache_once()

total, by_type = get_statistics()

counts = dict(by_type)

render_dashboard(
    counts,
    total,
    DISPLAY_NAMES,
)

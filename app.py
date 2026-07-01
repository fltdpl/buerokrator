import streamlit as st

from src.core.document_types import DOCUMENT_TYPE_LABELS
from src.database.statistics import get_statistics
from src.gui.views.dashboard import render_dashboard

DISPLAY_NAMES = dict(DOCUMENT_TYPE_LABELS)

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

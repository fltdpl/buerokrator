import streamlit as st

from src.gui.document_renderer import display_document
from src.gui.views.documents import render_documents_page

st.set_page_config(
    page_title="Dokumente",
    layout="wide",
)

render_documents_page(display_document)

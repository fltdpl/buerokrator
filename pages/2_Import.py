import streamlit as st

from src.gui.views.import_page import render_import_page

st.set_page_config(
    page_title="Import",
    layout="wide",
)

render_import_page()

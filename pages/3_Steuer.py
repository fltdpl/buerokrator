import streamlit as st

from src.gui.views.tax import render_tax_page

st.set_page_config(
    page_title="Steuer",
    layout="wide",
)

render_tax_page()

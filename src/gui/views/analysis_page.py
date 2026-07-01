import streamlit as st

from src.core.document_types import INSURANCE, INVOICE, PENSION, TAX
from src.database.statistics import get_statistics


def render_analysis_page():

    st.title("📊 Analyse")

    total, by_type = get_statistics()

    counts = dict(by_type)

    st.subheader("Dokumentübersicht")

    st.write(f"Gesamtzahl Dokumente: {total}")

    st.write(f"Rechnungen: {counts.get(INVOICE, 0)}")

    st.write(f"Versicherungen: {counts.get(INSURANCE, 0)}")

    st.write(f"Vorsorge: {counts.get(PENSION, 0)}")

    st.write(f"Steuern: {counts.get(TAX, 0)}")

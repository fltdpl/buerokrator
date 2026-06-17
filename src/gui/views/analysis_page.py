import streamlit as st

from src.database.statistics import get_statistics


def render_analysis_page():

    st.title("📊 Analyse")

    total, by_type = get_statistics()

    counts = dict(by_type)

    st.subheader("Dokumentübersicht")

    st.write(f"Gesamtzahl Dokumente: {total}")

    st.write(f"Rechnungen: {counts.get('invoice', 0)}")

    st.write(f"Versicherungen: {counts.get('insurance', 0)}")

    st.write(f"Vorsorge: {counts.get('pension', 0)}")

    st.write(f"Steuern: {counts.get('tax', 0)}")

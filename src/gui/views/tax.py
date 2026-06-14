import streamlit as st


def render_tax_page():

    st.title("💰 Steuer")

    year = st.sidebar.selectbox(
        "Steuerjahr",
        [
            2026,
            2025,
            2024,
        ],
    )

    st.info("Analysefunktionen folgen später.")

    st.write(f"Ausgewähltes Jahr: {year}")

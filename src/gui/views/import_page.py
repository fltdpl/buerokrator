from pathlib import Path

import streamlit as st

from src.processor.document_processor import process


def render_import_page():

    st.title("📥 Dokument importieren")

    uploaded_file = st.file_uploader(
        "PDF auswählen",
        type=["pdf"],
    )

    if uploaded_file:
        if st.button("Importieren und verarbeiten"):
            target = Path("inbox") / uploaded_file.name

            with open(
                target,
                "wb",
            ) as f:
                f.write(uploaded_file.getbuffer())

            process(str(target))

            st.success("Dokument archiviert")

            st.rerun()

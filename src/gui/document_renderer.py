import base64
from pathlib import Path

import streamlit as st

from src.gui.document_view import display_metadata

DISPLAY_NAMES = {
    "invoice": "🧾 Rechnungen",
    "insurance": "🛡 Versicherungen",
    "pension": "👴 Vorsorge",
    "tax": "🏛 Steuern",
    "unknown": "❓ Sonstiges",
}


def display_document(row):

    filename = row[0]
    archive_path = row[1]
    document_type = row[2]
    extracted_data = row[3]

    title = f"{DISPLAY_NAMES.get(document_type, document_type)} - {filename}"

    with st.expander(title):
        left_col, right_col = st.columns([1, 2])

        pdf_path = Path(archive_path)

        with left_col:
            st.write(f"**Pfad:** {archive_path}")

            try:
                display_metadata(extracted_data)

            except Exception:
                st.write(extracted_data)

            if pdf_path.exists():
                with open(pdf_path, "rb") as file:
                    st.download_button(
                        "📄 PDF herunterladen",
                        data=file,
                        file_name=filename,
                        key=f"download_{filename}",
                    )

        with right_col:
            if pdf_path.exists():
                with open(pdf_path, "rb") as pdf_file:
                    base64_pdf = base64.b64encode(pdf_file.read()).decode("utf-8")

                pdf_display = f"""
                <iframe
                    src="data:application/pdf;base64,{base64_pdf}"
                    width="100%"
                    height="1200"
                    type="application/pdf">
                </iframe>
                """

                st.markdown(
                    pdf_display,
                    unsafe_allow_html=True,
                )

            else:
                st.warning("PDF-Datei nicht gefunden.")

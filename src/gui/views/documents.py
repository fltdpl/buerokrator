import json

import streamlit as st

from src.database.export_csv import export_documents_csv
from src.database.list_documents import list_documents
from src.database.search import search_documents


def render_documents_page(display_document):

    st.title("📂 Dokumente")

    st.sidebar.subheader("Filter")

    search_term = st.sidebar.text_input("Volltext")

    selected_type = st.sidebar.selectbox(
        "Kategorie",
        [
            "Alle",
            "invoice",
            "insurance",
            "pension",
            "tax",
            "unknown",
        ],
    )

    selected_status = st.sidebar.selectbox(
        "Status",
        [
            "Alle",
            "Ungeprüft",
            "Geprüft",
        ],
    )

    selected_year = st.sidebar.selectbox(
        "Jahr",
        [
            "Alle",
            "2026",
            "2025",
            "2024",
        ],
    )

    issuer_filter = st.sidebar.text_input("Anbieter")

    filename_filter = st.sidebar.text_input("Dateiname")

    st.sidebar.markdown("---")

    # Ausgangsmenge bestimmen
    if search_term:
        documents = search_documents(search_term)

    else:
        documents = list_documents()

    # Kategorie filtern
    if selected_type != "Alle":
        documents = [row for row in documents if row[2] == selected_type]

    # Status filtern
    if selected_status != "Alle":
        verified_value = 0 if selected_status == "Ungeprüft" else 1

        documents = [row for row in documents if row[4] == verified_value]

    # Jahr filtern
    if selected_year != "Alle":
        documents = [row for row in documents if selected_year in row[1]]

    # Anbieter filtern
    if issuer_filter:
        issuer_filter = issuer_filter.lower().strip()

        filtered = []

        for row in documents:
            try:
                data = json.loads(row[3])

                issuer = data.get("issuer") or data.get("insurer") or ""

                if issuer_filter in issuer.lower():
                    filtered.append(row)

            except Exception:
                pass

        documents = filtered

    # Dateiname filtern
    if filename_filter:
        filename_filter = filename_filter.lower().strip()

        documents = [row for row in documents if filename_filter in row[0].lower()]

    st.caption(f"{len(documents)} Dokumente gefunden")

    csv_data = export_documents_csv(documents)

    st.sidebar.download_button(
        "📥 CSV Export",
        data=csv_data,
        file_name="buerokrator_export.csv",
        mime="text/csv",
    )

    for row in documents:
        display_document(row)

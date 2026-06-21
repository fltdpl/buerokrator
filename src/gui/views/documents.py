import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.core.document_display import get_document_display_name
from src.database.export_csv import export_documents_csv
from src.database.list_documents import list_documents
from src.database.search import search_documents
from src.database.statistics import get_verification_statistics

DISPLAY_NAMES = {
    "invoice": "Rechnung",
    "insurance": "Versicherung",
    "pension": "Vorsorge",
    "tax": "Steuer",
    "bank": "Bank",
    "housing": "Wohnen",
    "unknown": "Sonstiges",
}


def render_documents_page(display_document):

    st.title("📂 Dokumente")

    if "document_view" not in st.session_state:
        st.session_state["document_view"] = "list"

    st.sidebar.subheader("Filter")

    stats = get_verification_statistics()

    st.sidebar.caption(f"🟡 {stats[0]} ungeprüft")
    st.sidebar.caption(f"🟢 {stats[1]} geprüft")

    # st.sidebar.markdown("---")

    search_term = st.sidebar.text_input("Volltext")

    selected_type = st.sidebar.selectbox(
        "Kategorie",
        [
            "Alle",
            "invoice",
            "insurance",
            "pension",
            "tax",
            "bank",
            "housing",
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

    # Dokumente laden

    if search_term:
        documents = search_documents(search_term)

    else:
        documents = list_documents()

    # Kategorie filtern

    if selected_type != "Alle":
        documents = [row for row in documents if row[3] == selected_type]

    # Status filtern

    if selected_status != "Alle":
        verified_value = 0 if selected_status == "Ungeprüft" else 1

        documents = [row for row in documents if row[5] == verified_value]

    # Jahr filtern

    if selected_year != "Alle":
        documents = [row for row in documents if selected_year in row[2]]

    # Anbieter filtern

    if issuer_filter:
        issuer_filter = issuer_filter.lower().strip()

        filtered = []

        for row in documents:
            try:
                data = json.loads(row[4])

                issuer = data.get("issuer") or data.get("insurer") or ""

                if issuer_filter in issuer.lower():
                    filtered.append(row)

            except Exception:
                pass

        documents = filtered

    # Dateiname filtern

    if filename_filter:
        filename_filter = filename_filter.lower().strip()

        documents = [row for row in documents if filename_filter in row[1].lower()]

    st.caption(f"{len(documents)} Dokumente gefunden")

    csv_data = export_documents_csv(documents)

    st.sidebar.download_button(
        "📥 CSV Export",
        data=csv_data,
        file_name="buerokrator_export.csv",
        mime="text/csv",
    )

    if not documents:
        st.info("Keine Dokumente gefunden.")

        return

    if st.session_state["document_view"] == "details":
        selected_document_id = st.session_state.get("selected_document_id")
        selected_row = next(
            (row for row in documents if row[0] == selected_document_id),
            None,
        )

        if selected_row:
            display_document(
                selected_row,
                show_back_button=True,
            )

            return

    table_rows = []

    for row in documents:
        document_id = row[0]
        filename = row[1]
        archive_path = row[2]
        document_type = row[3]
        verified = row[5]
        created_at = row[6]

        try:
            data = json.loads(row[4])

        except Exception:
            data = {}

        try:
            created_at = datetime.fromisoformat(
                str(created_at).replace("Z", "")
            ).strftime("%d.%m.%Y")

        except Exception:
            created_at = "-"

        try:
            file_size = Path(archive_path).stat().st_size

            if file_size < 1024:
                size_text = f"{file_size} B"

            elif file_size < 1024 * 1024:
                size_text = f"{file_size / 1024:.0f} KB"

            else:
                size_text = f"{file_size / 1024 / 1024:.1f} MB"

        except Exception:
            size_text = "-"

        display_name = get_document_display_name(
            document_type,
            data,
        )

        table_rows.append(
            {
                "ID": document_id,
                "Status": "🟢" if verified else "🟡",
                "Dateiname": display_name,
                "Originaldatei": filename,
                "Kategorie": document_type,
                "Erstellt": created_at or "-",
                "Größe": size_text,
            }
        )

    st.subheader("Dokumente")

    if "selected_document_id" not in st.session_state:
        st.session_state["selected_document_id"] = table_rows[0]["ID"]

    if "document_mode" not in st.session_state:
        st.session_state["document_mode"] = "details"

    if st.session_state["document_view"] == "list":
        header1, header2, header3, header4, header5, header6 = st.columns(
            [0.5, 6, 2, 2, 1.5, 0.5]
        )

        with header1:
            st.caption("Status")

        with header2:
            st.caption("Dokument")

        with header3:
            st.caption("Kategorie")

        with header4:
            st.caption("Erstellt")

        with header5:
            st.caption("Größe")

        with header6:
            st.caption("Link")

        # st.divider()

        for item in table_rows:
            selected = item["ID"] == st.session_state["selected_document_id"]

            col1, col2, col3, col4, col5, col6 = st.columns([0.5, 6, 2, 2, 1.5, 0.5])

            with col1:
                st.write(item["Status"])

            with col2:
                if selected:
                    st.markdown(f"**▶ {item['Dateiname']}**")

                else:
                    st.markdown(f"**{item['Dateiname']}**")

            with col3:
                st.caption(
                    DISPLAY_NAMES.get(
                        item["Kategorie"],
                        item["Kategorie"],
                    )
                )

            with col4:
                st.caption(item["Erstellt"])

            with col5:
                st.caption(item["Größe"])

            with col6:
                if st.button(
                    "👁️",
                    key=f"open_{item['ID']}",
                ):
                    st.session_state["selected_document_id"] = item["ID"]

                    st.session_state["document_view"] = "details"

                    st.rerun()

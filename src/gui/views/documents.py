import pandas as pd
import streamlit as st

from src.core.document_types import DOCUMENT_TYPES, DOCUMENT_TYPE_LABELS
from src.database.export_csv import export_documents_csv
from src.database.list_documents import (
    get_document,
    get_next_unverified_id,
    list_documents,
)
from src.database.search import search_documents
from src.database.statistics import get_verification_statistics
from src.services.document_service import (
    available_years,
    build_table_rows,
    filter_documents,
)


def _selected_document_id():
    """Aktuell ausgewählte Dokument-ID aus dem URL-Query-Parameter (oder None)."""
    raw = st.query_params.get("doc")

    if raw is None:
        return None

    try:
        return int(raw)

    except (TypeError, ValueError):
        return None


def _open_document(document_id):
    """Öffnet die Detailansicht und setzt die Tabellen-Auswahl zurück."""
    st.session_state["documents_table_nonce"] = (
        st.session_state.get("documents_table_nonce", 0) + 1
    )
    st.query_params["doc"] = str(document_id)
    st.rerun()


def render_documents_page(display_document):

    st.title("📂 Dokumente")

    flash = st.session_state.pop("flash", None)
    if flash:
        st.toast(flash)

    # Sprungmarke vom Dashboard ("Prüfen starten").
    open_doc_id = st.session_state.pop("open_doc_id", None)
    if open_doc_id is not None:
        st.query_params["doc"] = str(open_doc_id)

    # Detailansicht: Dokument direkt per ID laden (unabhängig von Filtern),
    # damit Änderungen sofort erscheinen und der Eintrag nicht durch einen
    # Filter verschwindet.
    selected_document_id = _selected_document_id()

    if selected_document_id is not None:
        selected_row = get_document(selected_document_id)

        if selected_row:
            # Streamlit kann den nativen "Dokumente"-Seitenlink nicht abfangen,
            # solange man bereits auf der Seite ist. Ein eigener Button in der
            # Seitenleiste kehrt zuverlässig zur Listenansicht zurück.
            if st.sidebar.button(
                "📋 Zur Übersicht",
                width="stretch",
            ):
                del st.query_params["doc"]
                st.rerun()

            next_unverified = get_next_unverified_id(
                exclude_id=selected_document_id
            )
            if next_unverified is not None:
                if st.sidebar.button(
                    "⏭ Nächstes ungeprüftes",
                    width="stretch",
                ):
                    st.query_params["doc"] = str(next_unverified)
                    st.rerun()

            display_document(selected_row)

            return

        # Veraltete/ungültige ID -> zurück zur Liste.
        del st.query_params["doc"]

    st.sidebar.subheader("Filter")

    stats = get_verification_statistics()

    st.sidebar.caption(f"🟡 {stats[0]} ungeprüft")
    st.sidebar.caption(f"🟢 {stats[1]} geprüft")

    # st.sidebar.markdown("---")

    search_term = st.sidebar.text_input("Volltext")

    selected_type = st.sidebar.selectbox(
        "Kategorie",
        ["Alle", *DOCUMENT_TYPES],
    )

    # Voreinstellung vom Dashboard ("X ungeprüft") übernehmen.
    status_options = ["Alle", "Ungeprüft", "Geprüft"]
    preset_status = st.session_state.pop("documents_preset_status", None)
    if preset_status in status_options:
        st.session_state["documents_filter_status"] = preset_status

    selected_status = st.sidebar.selectbox(
        "Status",
        status_options,
        key="documents_filter_status",
    )

    # Dokumente laden (früh, damit die Jahresauswahl datengetrieben ist)

    if search_term:
        documents = search_documents(search_term)

    else:
        documents = list_documents()

    years = available_years(documents)

    year_options = ["Alle", *[str(year) for year in reversed(years)]]

    selected_from_year = st.sidebar.selectbox("Jahr von", year_options)

    selected_to_year = st.sidebar.selectbox("Jahr bis", year_options)

    issuer_filter = st.sidebar.text_input("Anbieter")

    filename_filter = st.sidebar.text_input("Dateiname")

    st.sidebar.markdown("---")

    documents = filter_documents(
        documents,
        document_type=None if selected_type == "Alle" else selected_type,
        verified=None
        if selected_status == "Alle"
        else selected_status == "Geprüft",
        from_year=int(selected_from_year) if selected_from_year != "Alle" else None,
        to_year=int(selected_to_year) if selected_to_year != "Alle" else None,
        issuer=issuer_filter,
        filename=filename_filter,
    )

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

    table_rows = [
        {
            "ID": row["id"],
            "Status": "🟢" if row["verified"] else "🟡",
            "Jahr": str(row["year"]) if row["year"] else "-",
            "Dokument": row["display_name"],
            "Kategorie": DOCUMENT_TYPE_LABELS.get(
                row["document_type"],
                row["document_type"],
            ),
            "Importiert": row["created_at"],
            "Größe": row["file_size"],
        }
        for row in build_table_rows(documents)
    ]

    st.subheader("Dokumente")
    st.caption("Zeile anklicken, um das Dokument zu öffnen.")

    # st.dataframe statt handgebauter Spalten: sortierbar, kompakt und
    # performant auch bei vielen Dokumenten. Der Nonce im Widget-Key setzt
    # die Zeilenauswahl nach Rückkehr aus der Detailansicht zurück.
    nonce = st.session_state.get("documents_table_nonce", 0)

    event = st.dataframe(
        pd.DataFrame(table_rows),
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        key=f"documents_table_{nonce}",
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Status": st.column_config.TextColumn(width="small"),
            "Jahr": st.column_config.TextColumn(width="small"),
            "Dokument": st.column_config.TextColumn(width="large"),
        },
    )

    selected_rows = event.selection.rows

    if selected_rows:
        _open_document(table_rows[selected_rows[0]]["ID"])

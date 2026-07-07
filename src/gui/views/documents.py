import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.core.document_display import get_document_display_name
from src.core.document_types import DOCUMENT_TYPES, DOCUMENT_TYPE_LABELS
from src.database.export_csv import export_documents_csv
from src.database.list_documents import (
    get_document,
    get_next_unverified_id,
    list_documents,
)
from src.database.search import search_documents
from src.database.statistics import get_verification_statistics
from src.organizer.date_utils import year_from_archive_path


def _document_year(row):
    return year_from_archive_path(row[2])


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

    available_years = sorted(
        {
            year
            for year in (_document_year(row) for row in documents)
            if year is not None
        }
    )

    year_options = ["Alle", *[str(year) for year in reversed(available_years)]]

    selected_from_year = st.sidebar.selectbox("Jahr von", year_options)

    selected_to_year = st.sidebar.selectbox("Jahr bis", year_options)

    issuer_filter = st.sidebar.text_input("Anbieter")

    filename_filter = st.sidebar.text_input("Dateiname")

    st.sidebar.markdown("---")

    # Kategorie filtern

    if selected_type != "Alle":
        documents = [row for row in documents if row[3] == selected_type]

    # Status filtern

    if selected_status != "Alle":
        verified_value = 0 if selected_status == "Ungeprüft" else 1

        documents = [row for row in documents if row[5] == verified_value]

    # Jahr filtern (Bereich von/bis)

    from_year = int(selected_from_year) if selected_from_year != "Alle" else None
    to_year = int(selected_to_year) if selected_to_year != "Alle" else None

    if from_year is not None and to_year is not None and from_year > to_year:
        from_year, to_year = to_year, from_year

    if from_year is not None or to_year is not None:
        lower = from_year if from_year is not None else float("-inf")
        upper = to_year if to_year is not None else float("inf")

        documents = [
            row
            for row in documents
            if (year := _document_year(row)) is not None and lower <= year <= upper
        ]

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

        document_year = _document_year(row)

        display_name = get_document_display_name(
            document_type,
            data,
            year=document_year,
        )

        table_rows.append(
            {
                "ID": document_id,
                "Status": "🟢" if verified else "🟡",
                "Jahr": str(document_year) if document_year else "-",
                "Dokument": display_name,
                "Kategorie": DOCUMENT_TYPE_LABELS.get(
                    document_type,
                    document_type,
                ),
                "Importiert": created_at or "-",
                "Größe": size_text,
            }
        )

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

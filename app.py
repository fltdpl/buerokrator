import json
from pathlib import Path

import streamlit as st

from src.database.category_counts import get_category_counts
from src.database.list_documents import list_documents
from src.database.recent_documents import get_recent_documents
from src.database.search import search_documents
from src.database.statistics import get_statistics

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
        st.write(f"**Pfad:** {archive_path}")
        try:
            st.json(json.loads(extracted_data))
        except Exception:
            st.write(extracted_data)

        pdf_path = Path(archive_path)

        if pdf_path.exists():
            with open(pdf_path, "rb") as file:
                st.download_button(
                    "📄 PDF herunterladen",
                    data=file,
                    file_name=filename,
                    key=filename,
                )


st.set_page_config(
    page_title="Buerokrator",
    layout="wide",
)

st.title("📄 Buerokrator")

# Statistik
total, by_type = get_statistics()
counts = dict(by_type)

st.caption(f"{total} Dokumente archiviert")
st.subheader("Dashboard")
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Dokumente",
    total,
)

col2.metric(
    "Rechnungen",
    counts.get("invoice", 0),
)

col3.metric(
    "Versicherungen",
    counts.get("insurance", 0),
)

col4.metric(
    "Vorsorge",
    counts.get("pension", 0),
)

# Sidebar
st.sidebar.title("Dokumente")
selected_type = st.sidebar.radio(
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

st.sidebar.markdown("---")
st.sidebar.write(f"🧾 Rechnungen ({counts.get('invoice', 0)})")
st.sidebar.write(f"🛡 Versicherungen ({counts.get('insurance', 0)})")
st.sidebar.write(f"👴 Vorsorge ({counts.get('pension', 0)})")
st.sidebar.write(f"🏛 Steuern ({counts.get('tax', 0)})")
st.sidebar.write(f"❓ Sonstiges ({counts.get('unknown', 0)})")

# Suche
st.subheader("Suche")
search_term = st.text_input("Suchbegriff")

if search_term:
    results = search_documents(search_term)
    st.write(f"{len(results)} Treffer gefunden")

    for row in results:
        display_document(row)

else:
    st.subheader("Dokumente")
    if selected_type == "Alle":
        documents = list_documents()
    else:
        documents = list_documents(selected_type)

    for row in documents:
        display_document(row)

# Zuletzt archiviert
st.subheader("Zuletzt archiviert")
recent = get_recent_documents()
for row in recent:
    st.write(f"{DISPLAY_NAMES.get(row[1], row[1])} - {row[0]}")

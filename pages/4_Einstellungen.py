import streamlit as st

from src.core.config import (
    load_config,
    save_config,
)
from src.database.reset_database import reset_database_and_archive

st.set_page_config(
    page_title="Einstellungen",
    layout="wide",
)

st.title("⚙ Einstellungen")

config = load_config()

st.subheader("Klassifikation")

model = st.selectbox(
    "LLM Modell",
    [
        "gemma3:4b",
        "qwen3:1.7b",
        "llama3",
    ],
    index=[
        "gemma3:4b",
        "qwen3:1.7b",
        "llama3",
    ].index(config["classifier"]["model"])
    if config["classifier"]["model"]
    in [
        "gemma3:4b",
        "qwen3:1.7b",
        "llama3",
    ]
    else 0,
)

temperature = st.slider(
    "Temperatur",
    min_value=0.0,
    max_value=1.0,
    value=float(config["classifier"]["temperature"]),
    step=0.05,
)

max_input_chars = st.number_input(
    "Max Input Chars",
    min_value=100,
    max_value=20000,
    value=int(config["classifier"]["max_input_chars"]),
    step=100,
)

st.subheader("OCR")
ocr_language = st.text_input(
    "OCR Sprache",
    value=config["ocr"]["language"],
)

st.subheader("Pfade")
st.caption("Änderungen wirken erst nach einem Neustart der Anwendung.")
inbox_path = st.text_input("Inbox", value=config["paths"]["inbox"])
archive_path = st.text_input("Archiv", value=config["paths"]["archive"])
exports_path = st.text_input("Export", value=config["paths"]["exports"])
database_path = st.text_input("Datenbank", value=config["database"]["path"])

st.subheader("Logging")

log_level = st.selectbox(
    "Log Level",
    [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
    ],
    index=[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
    ].index(config["logging"]["level"]),
)

if st.button("💾 Speichern"):
    config["classifier"]["model"] = model
    config["classifier"]["temperature"] = temperature
    config["classifier"]["max_input_chars"] = int(max_input_chars)
    config["ocr"]["language"] = ocr_language
    config["logging"]["level"] = log_level
    config["paths"]["inbox"] = inbox_path
    config["paths"]["archive"] = archive_path
    config["paths"]["exports"] = exports_path
    config["database"]["path"] = database_path
    save_config(config)
    st.success("Einstellungen gespeichert.")

st.markdown("---")
st.subheader("🚨 Gefahrenzone")
st.caption(
    "Löscht alle archivierten Dokumente unwiderruflich und initialisiert "
    "die Datenbank neu."
)

# Erfolgsmeldung nach abgeschlossenem Reset (überlebt den st.rerun).
reset_result = st.session_state.pop("reset_done", None)
if reset_result is not None:
    st.success(f"Datenbank zurückgesetzt. {reset_result} Archiv-Einträge entfernt.")

if not st.session_state.get("confirm_reset"):
    # Bestätigungstext zurücksetzen, solange das Feld nicht angezeigt wird.
    st.session_state.pop("confirm_reset_text", None)

    if st.button("🗑 Datenbank & Archiv löschen"):
        st.session_state["confirm_reset"] = True
        st.rerun()

else:
    st.error(
        "**Wirklich alles löschen?** Alle archivierten Dokumente werden "
        "endgültig entfernt und die Datenbank wird neu initialisiert. "
        "Dieser Schritt kann nicht rückgängig gemacht werden."
    )

    confirm_text = st.text_input(
        "Zum Bestätigen LÖSCHEN eingeben",
        key="confirm_reset_text",
    )

    col_delete, col_cancel = st.columns(2)

    with col_delete:
        if st.button("Endgültig löschen", type="primary"):
            if confirm_text.strip().upper() == "LÖSCHEN":
                removed = reset_database_and_archive()

                st.session_state["confirm_reset"] = False
                st.session_state["reset_done"] = removed
                st.rerun()

            else:
                st.warning('Bitte "LÖSCHEN" eingeben, um zu bestätigen.')

    with col_cancel:
        if st.button("Abbrechen"):
            st.session_state["confirm_reset"] = False
            st.rerun()

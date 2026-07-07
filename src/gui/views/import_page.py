from pathlib import Path

import streamlit as st

from src.processor.batch_import import (
    find_inbox_documents,
    import_inbox_documents,
)


def render_batch_import():
    st.subheader("📦 Stapel-Import")
    st.caption(
        "Verarbeitet alle Dateien, die im Inbox-Ordner liegen, automatisch: "
        "klassifizieren, umbenennen, archivieren. Die Korrektur der erkannten "
        "Werte passiert danach auf der Dokumente-Seite (Prüf-Workflow)."
    )

    pending = find_inbox_documents()

    if not pending:
        st.info("Keine Dateien im Inbox-Ordner.")

    else:
        st.write(f"{len(pending)} Datei(en) im Inbox-Ordner gefunden:")
        for path in pending:
            st.caption(f"• {path.name}")

        if st.button("Alle importieren", type="primary"):
            progress = st.progress(0.0)
            status = st.empty()

            def on_progress(index, total, filename):
                status.write(f"Verarbeite {index + 1}/{total}: {filename}")
                progress.progress(index / total if total else 0.0)

            succeeded, failed = import_inbox_documents(on_progress)

            progress.progress(1.0)
            status.empty()

            st.success(
                f"{len(succeeded)} Dokument(e) archiviert. "
                "Zum Prüfen auf die Dokumente-Seite wechseln (Filter: Ungeprüft)."
            )

            if failed:
                st.error(f"{len(failed)} Dokument(e) fehlgeschlagen:")
                for name in failed:
                    st.caption(f"• {name}")


def render_upload():
    """Dateien in die Inbox hochladen; die Verarbeitung übernimmt der
    Stapel-Import. Ein Weg für alles statt eines zweiten Analyse-Flows."""
    st.subheader("⬆️ Dateien hochladen")
    st.caption("Legt die Dateien in den Inbox-Ordner für den Stapel-Import.")

    uploaded_files = st.file_uploader(
        "PDF oder Bild auswählen",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key=f"upload_{st.session_state.get('upload_nonce', 0)}",
    )

    if uploaded_files and st.button("In Inbox übernehmen"):
        inbox = Path("inbox")
        inbox.mkdir(exist_ok=True)

        for uploaded_file in uploaded_files:
            target = inbox / uploaded_file.name
            with open(target, "wb") as f:
                f.write(uploaded_file.getbuffer())

        # Uploader über neuen Key leeren, sonst bietet er dieselben Dateien
        # nach dem Rerun erneut an.
        st.session_state["upload_nonce"] = (
            st.session_state.get("upload_nonce", 0) + 1
        )
        st.session_state["flash"] = f"{len(uploaded_files)} Datei(en) in der Inbox"

        st.rerun()


def render_import_page():
    st.title("📥 Dokument importieren")

    flash = st.session_state.pop("flash", None)
    if flash:
        st.toast(flash)

    render_batch_import()

    st.markdown("---")

    render_upload()

"""NiceGUI-Frontend (Migrationsziel, läuft parallel zu Streamlit).

Start:
    python -m src.frontend.main        # http://localhost:8081

Das Frontend enthält nur Darstellung und Event-Verdrahtung; alle Logik
liegt in src/services (siehe docs/10_NiceGUI_Migration.md).
"""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from nicegui import app, ui

# Seiten registrieren (Import genügt, @ui.page dekoriert die Routen).
import src.frontend.pages.dashboard  # noqa: F401
import src.frontend.pages.document_detail  # noqa: F401
import src.frontend.pages.documents  # noqa: F401
import src.frontend.pages.import_page  # noqa: F401
import src.frontend.pages.settings  # noqa: F401
import src.frontend.pages.tax  # noqa: F401
from src.database.list_documents import get_document

HOST = "127.0.0.1"
PORT = 8081


@app.get("/pdf/{document_id}")
def serve_pdf(document_id: int):
    """Liefert das Archiv-PDF direkt aus — keine static/pdf-Kopien mehr.

    Bewusst über die Dokument-ID statt über Pfade (kein Zugriff auf
    beliebige Dateien) und nur an localhost gebunden.
    """
    row = get_document(document_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")

    path = Path(row[2])

    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF-Datei nicht gefunden")

    return FileResponse(path, media_type="application/pdf")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host=HOST,
        port=PORT,
        title="Buerokrator",
        language="de",
        reload=False,
        show=False,
    )

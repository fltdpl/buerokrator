"""NiceGUI-Frontend von Buerokrator.

Start:
    python -m src.frontend.main        # http://localhost:8081

Das Frontend enthält nur Darstellung und Event-Verdrahtung; alle Logik
liegt in src/services.
"""

import os
from pathlib import Path

from src.core.app_home import get_app_home

# NiceGUI legt sein Storage-Verzeichnis standardmäßig relativ zur cwd an.
# Vor dem ersten nicegui-Import ins App-Home umleiten (Packaging: keine
# cwd-relativen Pfade). setdefault, damit ein extern gesetzter Pfad gewinnt.
os.environ.setdefault("NICEGUI_STORAGE_PATH", str(get_app_home() / ".nicegui"))

from fastapi import HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from nicegui import app, ui  # noqa: E402

# Seiten registrieren (Import genügt, @ui.page dekoriert die Routen).
import src.frontend.pages.dashboard  # noqa: F401
import src.frontend.pages.document_detail  # noqa: F401
import src.frontend.pages.documents  # noqa: F401
import src.frontend.pages.help_page  # noqa: F401
import src.frontend.pages.import_page  # noqa: F401
import src.frontend.pages.settings  # noqa: F401
import src.frontend.pages.setup_page  # noqa: F401
import src.frontend.pages.tax  # noqa: F401
import src.frontend.pages.trash  # noqa: F401
from src.database.list_documents import get_document

HOST = "127.0.0.1"
PORT = 8081

# Logo: im Repo unter assets/, im PyInstaller-Bundle via Spec-datas am
# selben relativen Ort (parents[2] = Repo-Root bzw. Bundle-Root).
_FAVICON = Path(__file__).resolve().parents[2] / "assets" / "buerokrator.svg"


@app.get("/pdf/{document_id}")
def serve_pdf(document_id: int):
    """Liefert das Archiv-PDF direkt aus — keine static/pdf-Kopien mehr.

    Bewusst über die Dokument-ID statt über Pfade (kein Zugriff auf
    beliebige Dateien) und nur an localhost gebunden.

    Bewusste Abwägung (Review P4): kein Auth — jeder lokale Prozess kann
    bei laufender App PDFs über fortlaufende IDs abrufen. Für den
    Ein-Nutzer-Betrieb auf 127.0.0.1 akzeptiert; SOBALD Mehrbenutzer/
    Accounts kommen, braucht diese Route eine Zugriffsprüfung.
    """
    row = get_document(document_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")

    path = Path(row["archive_path"])

    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF-Datei nicht gefunden")

    return FileResponse(path, media_type="application/pdf")


def run(*, show: bool = False) -> None:
    """Startet die App (auch Einstiegspunkt für das gepackte Bundle)."""
    ui.run(
        host=HOST,
        port=PORT,
        title="Buerokrator",
        language="de",
        favicon=str(_FAVICON) if _FAVICON.exists() else None,
        reload=False,
        show=show,
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()

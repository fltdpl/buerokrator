"""NiceGUI-Frontend von Buerokrator.

Start:
    python -m src.frontend.main        # http://localhost:8081

Das Frontend enthält nur Darstellung und Event-Verdrahtung; alle Logik
liegt in src/services.
"""

import os
import socket
import urllib.request
import webbrowser
from pathlib import Path

from src.core.app_home import get_base_home

# NiceGUI legt sein Storage-Verzeichnis standardmäßig relativ zur cwd an.
# Vor dem ersten nicegui-Import ins Basisverzeichnis umleiten (Packaging:
# keine cwd-relativen Pfade). setdefault, damit ein extern gesetzter Pfad
# gewinnt. Basis statt Profil (ADR 015): der Wert wird einmal beim Import
# gesetzt und könnte einem Profilwechsel nicht folgen — es ist UI-Zustand
# des Prozesses, kein Bestandteil eines Dokumentenbestands.
os.environ.setdefault("NICEGUI_STORAGE_PATH", str(get_base_home() / ".nicegui"))

from fastapi import HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from nicegui import app, ui  # noqa: E402

# Seiten registrieren (Import genügt, @ui.page dekoriert die Routen).
import src.frontend.pages.analyse  # noqa: F401
import src.frontend.pages.dashboard  # noqa: F401
import src.frontend.pages.document_detail  # noqa: F401
import src.frontend.pages.documents  # noqa: F401
import src.frontend.pages.help_page  # noqa: F401
import src.frontend.pages.import_page  # noqa: F401
import src.frontend.pages.migration_page  # noqa: F401
import src.frontend.pages.settings  # noqa: F401
import src.frontend.pages.setup_page  # noqa: F401
import src.frontend.pages.trash  # noqa: F401
from src.database.list_documents import get_document
from src.services.profile_service import ensure_active_profile

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


def _port_status() -> str:
    """Belegung von HOST:PORT — "frei", "buerokrator" oder "fremd".

    Im Browser-Modus beendet ein geschlossener Tab den Prozess nicht (dafür
    gibt es den Beenden-Knopf) — ein zweiter Start über das Anwendungsmenü
    traf dann auf den belegten Port und starb stumm am Bind-Fehler.
    """
    with socket.socket() as sock:
        sock.settimeout(1.0)

        if sock.connect_ex((HOST, PORT)) != 0:
            return "frei"

    try:
        with urllib.request.urlopen(
            f"http://{HOST}:{PORT}/", timeout=3
        ) as response:
            body = response.read(8192).decode("utf-8", errors="ignore")

        if "buerokrator" in body.lower():
            return "buerokrator"

    except Exception:
        pass

    return "fremd"


def run(*, show: bool = False) -> None:
    """Startet die App (auch Einstiegspunkt für das gepackte Bundle).

    Läuft bereits eine Instanz, wird nur der Browser zu ihr geöffnet —
    das ist beim Klick im Anwendungsmenü das erwartete Verhalten.
    """
    # Unter pytest keinen Port-Check: die User-Fixture der Smoke-Tests
    # führt diese Datei mit gemocktem ui.run aus — parallel darf die echte
    # App laufen, ohne dass der Check hier abbiegt.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        status = "frei"

    else:
        status = _port_status()

    if status == "buerokrator":
        print(
            "Buerokrator läuft bereits — öffne die laufende Instanz "
            f"unter http://{HOST}:{PORT} im Browser."
        )
        webbrowser.open(f"http://{HOST}:{PORT}")
        return

    if status == "fremd":
        print(
            f"Start abgebrochen: Port {PORT} auf {HOST} ist durch ein "
            "anderes Programm belegt."
        )
        raise SystemExit(1)

    # Zeigt das zuletzt aktive Profil ins Leere (verschoben, gelöscht,
    # externer Datenträger nicht eingehängt), würde die App es stillschweigend
    # neu anlegen und wie eine leere Installation aussehen. Lieber auf ein
    # vorhandenes zurückfallen und es sagen.
    hinweis = ensure_active_profile()

    if hinweis:
        print(hinweis)

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

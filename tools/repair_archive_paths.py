"""Archivpfade wieder an das aktuelle Archiv binden — Kommandozeilen-Fassung.

    python -m tools.repair_archive_paths            # nur pruefen
    python -m tools.repair_archive_paths --schreiben # reparieren

Die Logik steht in `src/services/archive_repair.py`; sie wird auch aus der
App heraus angeboten (Einstellungen → Datenbank → Archivpfade), weil eine
Paket-Installation weder Python noch dieses Verzeichnis mitbringt.

⚠️ Aus einem FREMDEN Arbeitsverzeichnis starten. Alte Eintraege koennen
relative Pfade tragen; die loesen gegen das Arbeitsverzeichnis auf und waeren
von der Basis aus zufaellig gruen.
"""

import socket
import sys

from src.core.app_home import get_app_home
from src.services.archive_repair import pruefe_archivpfade, repariere_archivpfade


def _verweigere_bei_laufender_app(host: str = "127.0.0.1", port: int = 8081) -> None:
    """Bricht ab, wenn die App laeuft — sie koennte gerade importieren."""
    with socket.socket() as sock:
        sock.settimeout(1.0)

        if sock.connect_ex((host, port)) == 0:
            raise RuntimeError(
                f"Auf {host}:{port} laeuft etwas — vermutlich Buerokrator. "
                "Bitte die App beenden und erneut versuchen."
            )


def _orte():
    from src.core.config import load_config

    config = load_config()

    return config["database"]["path"], config["paths"]["archive"]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    schreiben = "--schreiben" in argv

    db_path, archiv = _orte()

    print(f"Profil:    {get_app_home()}")
    print(f"Archiv:    {archiv}")

    if not schreiben:
        bericht = pruefe_archivpfade(db_path, archiv)
        print(f"\nDokumente gesamt:  {bericht['gesamt']}")
        print(f"In Ordnung:        {bericht['in_ordnung']}")
        print(f"Reparierbar:       {bericht['reparierbar']}")
        print(f"Ungeloest:         {bericht['ungeloest']}")
        print(f"Kollisionen:       {bericht['kollisionen']}")

        if bericht["ungeloeste_ids"]:
            print(f"Ungeloeste IDs:    {bericht['ungeloeste_ids'][:20]}")

        if bericht["reparierbar"]:
            print("\nTrockenlauf. Zum Schreiben: --schreiben")

        return 0

    try:
        _verweigere_bei_laufender_app()

    except RuntimeError as fehler:
        print(f"Abgebrochen: {fehler}")
        return 1

    bericht = repariere_archivpfade(db_path, archiv)

    print(f"\nRepariert:         {bericht['repariert']}")
    print(f"In Ordnung:        {bericht['in_ordnung']}")
    print(f"Ungeloest:         {bericht['ungeloest']}")
    print(f"Kollisionen:       {bericht['kollisionen']}")
    print(f"Sicherung:         {bericht['sicherung'] or 'nicht noetig'}")

    if bericht["ungeloeste_ids"]:
        print(f"Ungeloeste IDs:    {bericht['ungeloeste_ids'][:20]}")

    print("\nApp starten und stichprobenartig Dokumente oeffnen.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

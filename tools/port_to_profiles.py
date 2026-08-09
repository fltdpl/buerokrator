"""Einmaliger Umzug eines profillosen Bestands — Kommandozeilen-Fassung.

    python -m tools.port_to_profiles

Die Logik steht in `src/services/profile_port.py`; sie wird auch aus der App
heraus angeboten, weil eine Paket-Installation weder Python noch dieses
Verzeichnis mitbringt. Hier bleibt nur, was zur Kommandozeile gehört: die
Ausgabe — und die Sperre gegen eine laufende App.

⚠️ Aus einem FREMDEN Arbeitsverzeichnis starten. Die Gegenprobe des Umzugs
prüft, ob jede Archivdatei am neuen Ort liegt; ein relativer Pfad löst gegen
das Arbeitsverzeichnis auf und wäre von dort zufällig grün.
"""

import sys

from src.core.app_home import get_base_home
from src.services.profile_port import enable_profiles, profiles_enabled


def _verweigere_bei_laufender_app(host: str = "127.0.0.1", port: int = 8081) -> None:
    """Bricht ab, wenn die App läuft.

    Sie könnte gerade importieren und schriebe dann in einen Bestand, den
    dieses Werkzeug unter ihr wegzieht. Die Job-Sperre der App hilft hier
    nicht: sie ist prozesslokal, und das Werkzeug läuft in einem eigenen
    Prozess. Der belegte Port ist das einzige Signal, das prozessübergreifend
    verfügbar ist.
    """
    import socket

    with socket.socket() as sock:
        sock.settimeout(1.0)

        if sock.connect_ex((host, port)) == 0:
            raise RuntimeError(
                f"Auf {host}:{port} läuft etwas — vermutlich Buerokrator. "
                "Bitte die App beenden und erneut versuchen."
            )


def main() -> int:
    if profiles_enabled():
        print("Diese Installation hat bereits Profile — nichts zu tun.")
        return 0

    basis = get_base_home()
    print(f"Basis: {basis}")

    try:
        bericht = enable_profiles(vorpruefung=_verweigere_bei_laufender_app)

    except RuntimeError as fehler:
        print(f"Abgebrochen: {fehler}")
        return 1

    print(f"Umgeschriebene Dokumentpfade: {bericht['umgeschrieben']}")
    print(f"Gegengeprueft:                {bericht['geprueft']}")
    print(f"Bestand liegt jetzt unter:    {bericht['profil']}")
    print(f"Originale als Sicherung in:   {bericht['altbestand']}")
    print("\nApp starten und stichprobenartig Dokumente oeffnen. Erst danach")
    print("den Altbestand von Hand loeschen.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

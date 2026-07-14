"""DEPRECATED: Alt-Entrypoint (Live-Ordner-Watcher).

Der unterstützte Weg ist die App mit Stapel-Import:

    python -m src.frontend.main

Dieser Watcher bleibt vorerst lauffähig, wird aber nicht weiterentwickelt
und kennt z. B. keine Dubletten-Erkennung. (pytest lädt ihn wegen
`main_file = src/frontend/main.py` in pytest.ini bewusst nicht.)
"""

from src.watcher.folder_watcher import start_watcher

if __name__ == "__main__":
    print("HINWEIS: Dieser Watcher ist veraltet — empfohlen ist:")
    print("  python -m src.frontend.main")
    print("Buerokrator-Watcher startet trotzdem...")
    start_watcher("inbox")

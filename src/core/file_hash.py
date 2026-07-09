"""Inhalts-Hash einer Datei — Grundlage der Dubletten-Erkennung.

Bewusst über den Inhalt, nicht über den Dateinamen: dieselbe Rechnung kommt
als `rechnung.pdf` und `rechnung (1).pdf` in die Inbox. Umgekehrt sind zwei
Dokumente mit gleichem Namen und unterschiedlichem Inhalt keine Dubletten.
"""

import hashlib

# Blockweise lesen, damit auch große Scans nicht komplett in den Speicher
# müssen.
_CHUNK_SIZE = 128 * 1024


def file_hash(path):
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)

    return digest.hexdigest()

"""Erreichbarkeits-Check für Ollama.

Ollama ist optional: Ohne erreichbaren Dienst läuft der Import im
eingeschränkten Modus (nur Regel-Klassifikation, keine Feld-Extraktion).
Wo ein stiller Ausfall Schaden anrichten würde (erneute Analyse geprüfter
Dokumente, Qualitätsmessung), wird vorher explizit geprüft.
"""

import ollama


def is_ollama_available() -> bool:
    try:
        ollama.list()

    except Exception:
        return False

    return True

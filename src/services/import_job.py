"""Serverweiter Fortschritt des Stapel-Imports (framework-frei, testbar).

Der Stapel-Import läuft in NiceGUI in einem app-globalen Hintergrund-Task
(`background_tasks.create_or_defer`, nicht am Browser-Tab gebunden) — er
läuft also auch weiter, wenn man die Seite wechselt oder das Tab schließt.
Ohne diesen Modul-globalen State hing die Fortschritts-/Ergebnisanzeige aber
an den UI-Elementen der Seite, die den Import gestartet hat, und ging beim
Verlassen verloren. Dieser State macht Fortschritt und letztes Ergebnis für
jede /import-Seite sichtbar, egal wann sie (neu) geöffnet wird.
"""

_STATE = {
    "running": False,
    "index": 0,
    "total": 0,
    "current_filename": "",
    "result": None,
    # Klartext-Fehlermeldung des letzten Laufs (None = kein Fehler). Ohne
    # sauberes Zurücksetzen im Fehlerfall bliebe running=True stehen und
    # würde jeden weiteren Import blockieren.
    "error": None,
}


def is_running():
    return _STATE["running"]


def start():
    """Markiert den Beginn eines Laufs. Wirft, wenn bereits einer läuft."""
    if _STATE["running"]:
        raise RuntimeError("Es läuft bereits ein Stapel-Import.")

    _STATE["running"] = True
    _STATE["index"] = 0
    _STATE["total"] = 0
    _STATE["current_filename"] = ""
    _STATE["result"] = None
    _STATE["error"] = None


def update_progress(index, total, filename):
    _STATE["index"] = index
    _STATE["total"] = total
    _STATE["current_filename"] = filename


def finish(succeeded, duplicates, failed):
    _STATE["running"] = False
    _STATE["error"] = None
    _STATE["result"] = {
        "succeeded": succeeded,
        "duplicates": duplicates,
        "failed": failed,
    }


def abort(message):
    """Beendet den Lauf nach einem Fehler: Job freigeben, Fehler merken."""
    _STATE["running"] = False
    _STATE["result"] = None
    _STATE["error"] = str(message)


def clear_result():
    _STATE["result"] = None
    _STATE["error"] = None


def get_state():
    return dict(_STATE)


def _reset_for_tests():
    """Nur für Tests: setzt den Modul-State zurück (er ist Prozess-global)."""
    _STATE["running"] = False
    _STATE["index"] = 0
    _STATE["total"] = 0
    _STATE["current_filename"] = ""
    _STATE["result"] = None
    _STATE["error"] = None

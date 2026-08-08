"""Läuft gerade ein Hintergrund-Job? (ADR 015, Schritt 3)

Eine Frage, eine Antwort — damit Aufrufer nicht jeden Job einzeln kennen
müssen. Heute gibt es genau einen (den Stapel-Import); Backup und
Neuanalyse wären die nächsten Kandidaten und kämen hier dazu.

Gebraucht wird das vom Profilwechsel: der Stapel-Import läuft in einem
app-globalen Hintergrund-Task und löst seine Pfade **je Dokument** neu auf.
Ein Wechsel mitten im Lauf würde die restlichen Dokumente still in den
Bestand der anderen Person schreiben.
"""

from src.services import import_job


def running_job() -> "dict | None":
    """Der laufende Job mit Fortschritt, oder None."""
    state = import_job.get_state()

    if not state["running"]:
        return None

    return {
        "name": "Stapel-Import",
        "index": state["index"],
        "total": state["total"],
    }


def is_busy() -> bool:
    return running_job() is not None


def describe_running_job() -> "str | None":
    """Satz für Meldungen — „Stapel-Import läuft (12 von 30)".

    Der Fortschritt gehört dazu: eine nackte Absage lässt den Nutzer raten,
    wie lange er warten soll.
    """
    job = running_job()

    if job is None:
        return None

    if job["total"]:
        return f"{job['name']} läuft ({job['index']} von {job['total']})"

    return f"{job['name']} läuft"

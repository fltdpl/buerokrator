"""Framework-neutraler Zugriff auf das Anwendungs-Log (für die GUI)."""

from pathlib import Path

LOG_FILE = Path("logs") / "buerokrator.log"

LOG_LEVELS = ["ALLE", "INFO", "WARNING", "ERROR"]


def read_log_tail(max_lines=200, level=None, log_file=LOG_FILE):
    """Letzte Zeilen des Logs, optional nach Level gefiltert (neueste zuerst).

    Level-Filter arbeitet auf dem Format "... - LEVEL - ..." aus
    src/core/logger.py; unbekannt formatierte Zeilen bleiben bei "ALLE"
    sichtbar und werden sonst weggefiltert.
    """
    path = Path(log_file)

    if not path.exists():
        return []

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    except OSError:
        return []

    if level and level != "ALLE":
        lines = [line for line in lines if f" - {level} - " in line]

    return list(reversed(lines[-max_lines:]))

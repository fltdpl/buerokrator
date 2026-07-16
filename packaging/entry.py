"""PyInstaller-Einstiegspunkt für das gebündelte Buerokrator.

Eigenes Skript statt src/frontend/main.py, damit der Repo-Root als
Importbasis dient (``import src...``) und freeze_support gesetzt ist.
"""

import multiprocessing
import os
import sys

multiprocessing.freeze_support()

from src.core.app_home import get_app_home  # noqa: E402


def _redirect_output_to_logfile() -> None:
    """stdout/stderr des Bundles in eine Logdatei im App-Home umleiten.

    Über den Menüeintrag gestartet gibt es keine Konsole — Startmeldungen
    und vor allem unbehandelte Abstürze wären sonst unsichtbar. Pro Start
    überschrieben (nur der letzte Lauf ist für die Diagnose interessant).
    """
    log_dir = get_app_home() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    stream = open(log_dir / "console.log", "w", buffering=1, encoding="utf-8")

    try:
        os.chmod(log_dir / "console.log", 0o600)

    except OSError:
        pass

    sys.stdout = stream
    sys.stderr = stream


if getattr(sys, "frozen", False):
    _redirect_output_to_logfile()

from src.frontend.main import run  # noqa: E402

run(show=True)

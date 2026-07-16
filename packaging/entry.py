"""PyInstaller-Einstiegspunkt für das gebündelte Buerokrator.

Eigenes Skript statt src/frontend/main.py, damit der Repo-Root als
Importbasis dient (``import src...``) und freeze_support gesetzt ist.
"""

import multiprocessing

multiprocessing.freeze_support()

from src.frontend.main import run  # noqa: E402

run(show=True)

"""Einen Ordner im Dateimanager des Betriebssystems zeigen.

Framework-neutral und offline: gestartet wird ein Programm auf diesem
Rechner, es geht nichts nach außen.

Serverseitig ist hier richtig — Oberfläche und Bestand liegen auf derselben
Maschine (localhost, Einzelplatz, dieselbe Voraussetzung wie bei `/pdf/{id}`),
und ein Browser kann einen lokalen Ordner ohnehin nicht öffnen.
"""

import os
import subprocess
import sys
from pathlib import Path


def _saubere_umgebung():
    """Umgebung ohne die Bibliothekspfade des Release-Pakets.

    Im PyInstaller-Paket zeigt `LD_LIBRARY_PATH` auf die mitgelieferten
    Bibliotheken. Ein von dort gestartetes Systemprogramm (`xdg-open` ruft
    weitere) lädt dann unsere Fassung von glibc & Co. statt seiner eigenen
    und bricht ab — im Entwicklungsbetrieb fällt das nie auf, weil die
    Variable dort gar nicht gesetzt ist.

    Der Bootloader legt einen zuvor vorhandenen Wert unter
    `LD_LIBRARY_PATH_ORIG` ab (in der Bootloader-Binary von PyInstaller 6.21
    nachgesehen). Gab es keinen, gehört die Variable ganz weg. Außerhalb des
    Pakets wird die Umgebung nicht angefasst.
    """
    umgebung = dict(os.environ)

    if "LD_LIBRARY_PATH_ORIG" in umgebung:
        umgebung["LD_LIBRARY_PATH"] = umgebung.pop("LD_LIBRARY_PATH_ORIG")

    elif getattr(sys, "frozen", False):
        umgebung.pop("LD_LIBRARY_PATH", None)

    return umgebung


def oeffne_ordner(pfad):
    """Öffnet den Ordner im Dateimanager.

    Wirft `FileNotFoundError`, wenn es den Ordner nicht gibt (vor der ersten
    Sicherung der Normalfall) — angelegt wird er bewusst nicht: „Öffnen" darf
    nichts erschaffen. Fehlt das Öffnen-Programm selbst, wird daraus ein
    `RuntimeError` mit klarer Ursache; die rohe Meldung („No such file or
    directory: 'xdg-open'") ließe den Nutzer den Fehler bei seinem Ordner
    suchen.
    """
    ordner = Path(pfad)

    if not ordner.is_dir():
        raise FileNotFoundError(f"Der Ordner {ordner} existiert nicht.")

    if os.name == "nt":
        os.startfile(str(ordner))
        return

    try:
        # Popen statt run: manche Dateimanager kehren erst zurück, wenn ihr
        # Fenster geschlossen wird — die Oberfläche stünde so lange still.
        # start_new_session löst das Kind vom Prozess der App, damit es deren
        # Ende überlebt.
        subprocess.Popen(
            ["xdg-open", str(ordner)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=_saubere_umgebung(),
        )

    except FileNotFoundError as fehler:
        raise RuntimeError(
            "Kein Dateimanager gefunden (xdg-open fehlt)."
        ) from fehler

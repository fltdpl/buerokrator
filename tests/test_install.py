"""Installation/Update: packaging/install.sh gegen ein Attrappen-Paket.

Wie bei der Deinstallation zählt, was das Skript auf der Platte tatsächlich
tut. Kern ist das Update: früher löschte es die alte Installation, BEVOR die
neue kopiert war — ein Abbruch dazwischen (volle Platte, unlesbare Datei,
Strg+C) ließ gar keine Installation zurück.
"""

import os
import shutil
import subprocess
from pathlib import Path

PACKAGING = Path(__file__).resolve().parents[1] / "packaging"


def _paket(ort: Path, version: str) -> Path:
    """Baut nach, was build_linux.sh in den Tarball legt (ohne Icons)."""
    paket = ort / f"paket-{version}"
    programm = paket / "buerokrator"
    (programm / "_internal").mkdir(parents=True)
    starter = programm / "buerokrator"
    starter.write_text("#!/bin/sh\ntrue\n", encoding="utf-8")
    starter.chmod(0o755)
    (programm / "_internal" / f"nur-in-{version}.txt").write_text(version, encoding="utf-8")

    for name in ("install.sh", "uninstall.sh", "buerokrator.desktop"):
        shutil.copy(PACKAGING / name, paket / name)

    (paket / "VERSION").write_text(f"{version}\n", encoding="utf-8")

    return paket


def _installieren(home: Path, paket: Path) -> subprocess.CompletedProcess:
    umgebung = dict(os.environ)
    umgebung["HOME"] = str(home)
    umgebung.pop("XDG_DATA_HOME", None)
    umgebung.pop("BUEROKRATOR_HOME", None)

    return subprocess.run(
        ["bash", str(paket / "install.sh")],
        capture_output=True,
        text=True,
        env=umgebung,
        cwd=str(home),
        timeout=60,
    )


def _opt(home: Path) -> Path:
    return home / ".local" / "opt" / "buerokrator"


def _reste(home: Path) -> list[str]:
    """Alles neben der Installation, was nach einem Lauf nicht liegen bleiben darf."""
    return sorted(p.name for p in _opt(home).parent.iterdir() if p.name != "buerokrator")


def test_erstinstallation(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    ergebnis = _installieren(home, _paket(tmp_path, "1.0"))

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert (_opt(home) / "buerokrator").exists()
    assert (_opt(home) / "uninstall.sh").exists()
    assert (_opt(home) / "VERSION").read_text(encoding="utf-8").strip() == "1.0"
    assert (home / ".local" / "bin" / "buerokrator").is_symlink()
    assert _reste(home) == []


def test_update_ersetzt_die_alte_fassung_vollstaendig(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    _installieren(home, _paket(tmp_path, "1.0"))

    ergebnis = _installieren(home, _paket(tmp_path, "2.0"))

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert (_opt(home) / "VERSION").read_text(encoding="utf-8").strip() == "2.0"
    assert (_opt(home) / "_internal" / "nur-in-2.0.txt").exists()
    # Keine Dateien der Vorversion: PyInstaller-Bibliotheken zweier Stände
    # gemischt wären schlimmer als ein sauberer Fehlschlag.
    assert not (_opt(home) / "_internal" / "nur-in-1.0.txt").exists()
    assert _reste(home) == []


def test_abgebrochenes_update_laesst_die_alte_installation_stehen(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    _installieren(home, _paket(tmp_path, "1.0"))

    neu = _paket(tmp_path, "2.0")
    # Eine unlesbare Datei lässt cp mitten im Kopieren scheitern — derselbe
    # Zustand wie ein Abbruch durch volle Platte.
    kaputt = neu / "buerokrator" / "_internal" / "nur-in-2.0.txt"
    kaputt.chmod(0o000)

    try:
        ergebnis = _installieren(home, neu)
    finally:
        kaputt.chmod(0o644)

    assert ergebnis.returncode != 0
    assert (_opt(home) / "VERSION").read_text(encoding="utf-8").strip() == "1.0"
    assert (_opt(home) / "_internal" / "nur-in-1.0.txt").exists()
    assert (_opt(home) / "buerokrator").exists()


def test_reste_eines_abgebrochenen_laufs_stoeren_nicht(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    _installieren(home, _paket(tmp_path, "1.0"))
    halbfertig = _opt(home).parent / "buerokrator.neu"
    (halbfertig / "_internal").mkdir(parents=True)
    (halbfertig / "_internal" / "verwaist.txt").write_text("rest", encoding="utf-8")

    ergebnis = _installieren(home, _paket(tmp_path, "2.0"))

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert not (_opt(home) / "_internal" / "verwaist.txt").exists()
    assert _reste(home) == []

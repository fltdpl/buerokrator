"""Deinstallation: das Gegenstück zu packaging/install.sh.

Getestet wird das Shell-Skript selbst — als Subprozess gegen eine
Attrappen-Installation in einem eigenen HOME. Ein reiner Lesetest wäre hier
wertlos: die Gefahr steckt nicht im Text, sondern darin, was `rm -rf`
tatsächlich trifft.
"""

import os
import subprocess
from pathlib import Path

import pytest

PACKAGING = Path(__file__).resolve().parents[1] / "packaging"
SKRIPT = PACKAGING / "uninstall.sh"

ICON_ORTE = (
    ("scalable/apps", "buerokrator.svg"),
    ("256x256/apps", "buerokrator.png"),
    ("128x128/apps", "buerokrator.png"),
    ("64x64/apps", "buerokrator.png"),
)


def _installation_anlegen(home: Path) -> dict[str, Path]:
    """Baut nach, was install.sh verteilt — plus Nutzerdaten."""
    opt = home / ".local" / "opt" / "buerokrator"
    (opt / "_internal").mkdir(parents=True)
    (opt / "icons").mkdir()
    starter = opt / "buerokrator"
    starter.write_text("#!/bin/sh\ntrue\n", encoding="utf-8")
    starter.chmod(0o755)

    # exist_ok, weil die geteilten Verzeichnisse eine Deinstallation
    # überleben sollen — ein zweiter Aufbau trifft sie also schon an.
    bin_dir = home / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "buerokrator").symlink_to(starter)

    apps = home / ".local" / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    (apps / "buerokrator.desktop").write_text(
        f"[Desktop Entry]\nName=Buerokrator\nExec={starter}\n", encoding="utf-8"
    )

    icons = home / ".local" / "share" / "icons" / "hicolor"
    for unterordner, name in ICON_ORTE:
        ziel = icons / unterordner
        ziel.mkdir(parents=True, exist_ok=True)
        (ziel / name).write_text("bild", encoding="utf-8")

    daten = home / ".local" / "share" / "buerokrator"
    (daten / "profiles" / "1" / "database").mkdir(parents=True)
    (daten / "profiles" / "1" / "database" / "dokumente.db").write_text(
        "unantastbar", encoding="utf-8"
    )
    (daten / "config").mkdir()
    (daten / "config" / "settings.yaml").write_text("archiv: archive\n", encoding="utf-8")

    return {
        "opt": opt,
        "starter": bin_dir / "buerokrator",
        "desktop": apps / "buerokrator.desktop",
        "icons": icons,
        "daten": daten,
    }


def _lauf(home: Path, *argumente: str, eingabe: str = "") -> subprocess.CompletedProcess:
    umgebung = dict(os.environ)
    umgebung["HOME"] = str(home)
    # Ein gesetztes XDG_DATA_HOME oder BUEROKRATOR_HOME der Entwicklerkiste
    # würde das Skript auf den ECHTEN Bestand zeigen lassen.
    umgebung.pop("XDG_DATA_HOME", None)
    umgebung.pop("BUEROKRATOR_HOME", None)

    return subprocess.run(
        ["bash", str(SKRIPT), *argumente],
        input=eingabe,
        capture_output=True,
        text=True,
        env=umgebung,
        cwd=str(home),
        timeout=60,
    )


def _icons_vorhanden(icons: Path) -> list[Path]:
    return [icons / ordner / name for ordner, name in ICON_ORTE if (icons / ordner / name).exists()]


def test_entfernt_alle_vier_installationsorte(tmp_path):
    orte = _installation_anlegen(tmp_path)

    ergebnis = _lauf(tmp_path, "--ja")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert not orte["opt"].exists()
    assert not orte["starter"].exists() and not orte["starter"].is_symlink()
    assert not orte["desktop"].exists()
    assert _icons_vorhanden(orte["icons"]) == []


def test_nutzerdaten_bleiben_unangetastet(tmp_path):
    orte = _installation_anlegen(tmp_path)
    datenbank = orte["daten"] / "profiles" / "1" / "database" / "dokumente.db"

    ergebnis = _lauf(tmp_path, "--ja")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert datenbank.read_text(encoding="utf-8") == "unantastbar"
    assert (orte["daten"] / "config" / "settings.yaml").exists()
    # Der Nutzer muss erfahren, wo seine Daten geblieben sind.
    assert str(orte["daten"]) in ergebnis.stdout


def test_ohne_bestaetigung_passiert_nichts(tmp_path):
    orte = _installation_anlegen(tmp_path)

    ergebnis = _lauf(tmp_path, eingabe="n\n")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert orte["opt"].exists()
    assert orte["starter"].is_symlink()
    assert orte["desktop"].exists()


def test_leere_antwort_gilt_als_nein(tmp_path):
    orte = _installation_anlegen(tmp_path)

    ergebnis = _lauf(tmp_path, eingabe="\n")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert orte["opt"].exists()


def test_bestaetigung_mit_j_entfernt(tmp_path):
    orte = _installation_anlegen(tmp_path)

    ergebnis = _lauf(tmp_path, eingabe="j\n")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert not orte["opt"].exists()
    assert not orte["desktop"].exists()


def test_fremder_starter_gleichen_namens_bleibt(tmp_path):
    """~/.local/bin ist ein geteiltes Verzeichnis — dort wird nur der eigene
    Symlink entfernt, nie eine gleichnamige Datei von jemand anderem."""
    orte = _installation_anlegen(tmp_path)
    orte["starter"].unlink()
    orte["starter"].write_text("#!/bin/sh\necho fremd\n", encoding="utf-8")

    ergebnis = _lauf(tmp_path, "--ja")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert orte["starter"].read_text(encoding="utf-8") == "#!/bin/sh\necho fremd\n"
    assert not orte["opt"].exists()


def test_fremder_symlink_gleichen_namens_bleibt(tmp_path):
    orte = _installation_anlegen(tmp_path)
    anderes_ziel = tmp_path / "woanders"
    anderes_ziel.write_text("fremd", encoding="utf-8")
    orte["starter"].unlink()
    orte["starter"].symlink_to(anderes_ziel)

    ergebnis = _lauf(tmp_path, "--ja")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert orte["starter"].is_symlink()
    assert orte["starter"].resolve() == anderes_ziel


def test_daten_verschieben_loescht_nicht_sondern_raeumt_beiseite(tmp_path):
    orte = _installation_anlegen(tmp_path)

    ergebnis = _lauf(tmp_path, "--ja", "--daten-verschieben")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert not orte["daten"].exists()

    beiseite = sorted(tmp_path.glob("buerokrator-daten-*"))
    assert len(beiseite) == 1, ergebnis.stdout
    gerettet = beiseite[0] / "profiles" / "1" / "database" / "dokumente.db"
    assert gerettet.read_text(encoding="utf-8") == "unantastbar"
    assert str(beiseite[0]) in ergebnis.stdout


def test_daten_verschieben_ueberschreibt_kein_vorhandenes_ziel(tmp_path):
    orte = _installation_anlegen(tmp_path)
    ergebnis = _lauf(tmp_path, "--ja", "--daten-verschieben")
    assert ergebnis.returncode == 0, ergebnis.stderr

    # Zweiter Durchgang mit neuen Daten am selben Tag: das erste Paket
    # darf dabei nicht verlorengehen.
    orte = _installation_anlegen(tmp_path)
    (orte["daten"] / "profiles" / "1" / "database" / "dokumente.db").write_text(
        "zweiter satz", encoding="utf-8"
    )

    ergebnis = _lauf(tmp_path, "--ja", "--daten-verschieben")

    assert ergebnis.returncode == 0, ergebnis.stderr
    pakete = sorted(tmp_path.glob("buerokrator-daten-*"))
    assert len(pakete) == 2
    inhalte = {
        (paket / "profiles" / "1" / "database" / "dokumente.db").read_text(encoding="utf-8")
        for paket in pakete
    }
    assert inhalte == {"unantastbar", "zweiter satz"}


def test_daten_bleiben_wenn_buerokrator_home_gesetzt_ist(tmp_path):
    """Bei gesetztem BUEROKRATOR_HOME liegen die Daten woanders — dann lieber
    gar nichts anfassen als das falsche Verzeichnis verschieben."""
    orte = _installation_anlegen(tmp_path)
    umgebung = dict(os.environ)
    umgebung["HOME"] = str(tmp_path)
    umgebung.pop("XDG_DATA_HOME", None)
    umgebung["BUEROKRATOR_HOME"] = str(tmp_path / "eigener-ort")

    ergebnis = subprocess.run(
        ["bash", str(SKRIPT), "--ja", "--daten-verschieben"],
        input="",
        capture_output=True,
        text=True,
        env=umgebung,
        cwd=str(tmp_path),
        timeout=60,
    )

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert orte["daten"].exists()
    assert sorted(tmp_path.glob("buerokrator-daten-*")) == []
    assert "BUEROKRATOR_HOME" in ergebnis.stdout


def test_xdg_data_home_wird_fuer_die_daten_beachtet(tmp_path):
    orte = _installation_anlegen(tmp_path)
    xdg = tmp_path / "xdg"
    daten = xdg / "buerokrator" / "profiles" / "1"
    daten.mkdir(parents=True)
    (daten / "marker").write_text("hier", encoding="utf-8")

    umgebung = dict(os.environ)
    umgebung["HOME"] = str(tmp_path)
    umgebung["XDG_DATA_HOME"] = str(xdg)
    umgebung.pop("BUEROKRATOR_HOME", None)

    ergebnis = subprocess.run(
        ["bash", str(SKRIPT), "--ja", "--daten-verschieben"],
        input="",
        capture_output=True,
        text=True,
        env=umgebung,
        cwd=str(tmp_path),
        timeout=60,
    )

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert not (xdg / "buerokrator").exists()
    # Das Programm liegt trotz XDG unter ~/.local — genau wie install.sh es ablegt.
    assert not orte["opt"].exists()
    # Die Daten am Standardort waren gar nicht gemeint und bleiben liegen.
    assert orte["daten"].exists()


def test_nichts_installiert_ist_kein_fehler(tmp_path):
    (tmp_path / ".local").mkdir()

    ergebnis = _lauf(tmp_path, "--ja")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "nichts" in ergebnis.stdout.lower() or "keine" in ergebnis.stdout.lower()


def test_zweiter_lauf_ist_folgenlos(tmp_path):
    _installation_anlegen(tmp_path)
    assert _lauf(tmp_path, "--ja").returncode == 0

    ergebnis = _lauf(tmp_path, "--ja")

    assert ergebnis.returncode == 0, ergebnis.stderr


def test_geteilte_verzeichnisse_bleiben_stehen(tmp_path):
    """Nur die eigenen Dateien fliegen raus — nicht applications/ oder icons/
    selbst und schon gar nicht fremde Einträge darin."""
    orte = _installation_anlegen(tmp_path)
    apps = orte["desktop"].parent
    (apps / "fremdprogramm.desktop").write_text("[Desktop Entry]\n", encoding="utf-8")
    (orte["icons"] / "256x256" / "apps" / "fremd.png").write_text("bild", encoding="utf-8")

    ergebnis = _lauf(tmp_path, "--ja")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert apps.is_dir()
    assert (apps / "fremdprogramm.desktop").exists()
    assert (orte["icons"] / "256x256" / "apps" / "fremd.png").exists()
    assert (tmp_path / ".local" / "bin").is_dir()


def test_selbstloeschung_aus_dem_installationsverzeichnis(tmp_path):
    """Der ausgelieferte Deinstaller liegt IM Verzeichnis, das er löscht.
    Bash liest sein Skript währenddessen nach — ohne Vorkehrung bricht der
    Lauf mittendrin ab und lässt eine halb entfernte Installation zurück."""
    orte = _installation_anlegen(tmp_path)
    mitgeliefert = orte["opt"] / "uninstall.sh"
    mitgeliefert.write_bytes(SKRIPT.read_bytes())
    mitgeliefert.chmod(0o755)

    umgebung = dict(os.environ)
    umgebung["HOME"] = str(tmp_path)
    umgebung.pop("XDG_DATA_HOME", None)
    umgebung.pop("BUEROKRATOR_HOME", None)

    ergebnis = subprocess.run(
        ["bash", str(mitgeliefert), "--ja"],
        input="",
        capture_output=True,
        text=True,
        env=umgebung,
        cwd=str(tmp_path),
        timeout=60,
    )

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert not orte["opt"].exists()
    assert not orte["desktop"].exists()
    assert _icons_vorhanden(orte["icons"]) == []


def test_hilfe_erklaert_und_entfernt_nichts(tmp_path):
    orte = _installation_anlegen(tmp_path)

    ergebnis = _lauf(tmp_path, "--hilfe")

    assert ergebnis.returncode == 0
    assert "--daten-verschieben" in ergebnis.stdout
    assert orte["opt"].exists()


def test_unbekannte_option_bricht_ab(tmp_path):
    orte = _installation_anlegen(tmp_path)

    ergebnis = _lauf(tmp_path, "--alles-weg")

    assert ergebnis.returncode == 2
    assert "--alles-weg" in ergebnis.stderr
    assert orte["opt"].exists()
    assert orte["daten"].exists()


@pytest.mark.parametrize("skript", ["build_linux.sh", "install.sh"])
def test_deinstaller_wird_mit_ausgeliefert(skript):
    """Ohne diese beiden Stellen läge der Deinstaller nur im Repo: einmal im
    Tarball, einmal neben dem Programm — der Tarball wird nach der
    Installation üblicherweise gelöscht."""
    inhalt = (PACKAGING / skript).read_text(encoding="utf-8")

    assert "uninstall.sh" in inhalt

"""Profile anlegen, umbenennen, entfernen, Rückfall beim Start (Schritt 4).

Die Verwaltung fasst ganze Dokumentenbestände an. Entsprechend viel Gewicht
liegt hier auf dem, was sie **nicht** tut: löschen.
"""

import sqlite3

import pytest
import yaml

from src.core.app_home import get_app_home, reset_profile_cache
from src.services import import_job
from src.services.profile_service import (
    MAX_PROFILE,
    absolute_data_paths,
    activate_profile,
    active_profile,
    create_profile,
    ensure_active_profile,
    list_profiles,
    missing_profiles,
    profile_name,
    remove_profile,
    rename_profile,
)


@pytest.fixture(autouse=True)
def sauberer_zustand():
    reset_profile_cache()
    import_job._reset_for_tests()
    yield
    reset_profile_cache()
    import_job._reset_for_tests()


@pytest.fixture
def zwei_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text(
        yaml.safe_dump(
            {
                "paths": {"archive": "./archive"},
                "database": {"path": "./database/buerokrator.db"},
            }
        ),
        encoding="utf-8",
    )

    db = tmp_path / "database" / "buerokrator.db"
    db.parent.mkdir()
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, archive_path TEXT)")
    conn.commit()
    conn.close()

    rename_profile("1", "Person A")
    create_profile("Person B")

    return tmp_path


def test_drittes_profil_anlegen(zwei_profile):
    neu = create_profile("Kim")

    assert neu == "3"
    assert [p["name"] for p in list_profiles()] == ["Person A", "Person B", "Kim"]
    assert (zwei_profile / "profiles" / "3").is_dir()
    # Das aktive Profil bleibt, wo es war.
    assert active_profile() == "1"


def test_umbenennen_laesst_das_verzeichnis_in_ruhe(zwei_profile):
    vorher = sorted(p.name for p in (zwei_profile / "profiles").iterdir())

    rename_profile("2", "Person B neu")

    assert profile_name("2") == "Person B neu"
    assert sorted(p.name for p in (zwei_profile / "profiles").iterdir()) == vorher


def test_umbenennen_mit_umlauten_und_leerzeichen(zwei_profile):
    # Der Name landet nie in einem Pfad — dafür ist die Kennung fest.
    rename_profile("2", "Jörg Müller-Groß")

    assert profile_name("2") == "Jörg Müller-Groß"
    assert (zwei_profile / "profiles" / "2").is_dir()


def test_leerer_name_wird_abgelehnt(zwei_profile):
    with pytest.raises(RuntimeError, match="nicht leer"):
        rename_profile("2", "   ")

    assert profile_name("2") == "Person B"


def test_entfernen_loescht_keine_dateien(zwei_profile):
    verzeichnis = remove_profile("2")

    assert [p["id"] for p in list_profiles()] == ["1"]
    # Der Bestand liegt weiter da — Löschen bleibt eine bewusste Handarbeit.
    assert verzeichnis.is_dir()
    assert (verzeichnis / "profile.yaml").exists()


def test_das_geoeffnete_profil_laesst_sich_nicht_entfernen(zwei_profile):
    with pytest.raises(RuntimeError, match="Erst wechseln"):
        remove_profile("1")

    assert [p["id"] for p in list_profiles()] == ["1", "2"]


def test_das_letzte_profil_bleibt_erhalten(zwei_profile):
    # Es braucht keine eigene Regel dafür: das einzige verbliebene Profil
    # ist zwangsläufig das geöffnete, und das ist geschützt.
    remove_profile("2")

    with pytest.raises(RuntimeError, match="Erst wechseln"):
        remove_profile("1")

    assert [p["id"] for p in list_profiles()] == ["1"]


def test_entfernen_ist_waehrend_eines_imports_gesperrt(zwei_profile):
    import_job.start()

    with pytest.raises(RuntimeError, match="Stapel-Import läuft"):
        remove_profile("2")


def test_start_faellt_zurueck_wenn_das_aktive_profil_fehlt(zwei_profile):
    activate_profile("2")
    # Verzeichnis „verschwindet" — externer Datenträger, Verschieben, Löschen.
    (zwei_profile / "profiles" / "2" / "profile.yaml").unlink()
    (zwei_profile / "profiles" / "2").rmdir()
    reset_profile_cache()

    meldung = ensure_active_profile()

    assert meldung is not None
    assert "nicht gefunden" in meldung
    assert active_profile() == "1"
    assert get_app_home() == zwei_profile / "profiles" / "1"


def test_start_meldet_nichts_wenn_alles_stimmt(zwei_profile):
    assert ensure_active_profile() is None


def test_ohne_profile_meldet_der_start_nichts(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    assert ensure_active_profile() is None


def test_fehlende_verzeichnisse_werden_benannt(zwei_profile):
    (zwei_profile / "profiles" / "2" / "profile.yaml").unlink()
    (zwei_profile / "profiles" / "2").rmdir()

    assert missing_profiles() == ["2"]


def test_absolute_pfade_werden_fuer_die_warnung_gemeldet(zwei_profile):
    assert absolute_data_paths() == []

    einstellungen = zwei_profile / "config" / "settings.yaml"
    inhalt = yaml.safe_load(einstellungen.read_text(encoding="utf-8"))
    inhalt["paths"]["archive"] = "/woanders/archive"
    einstellungen.write_text(yaml.safe_dump(inhalt), encoding="utf-8")

    assert absolute_data_paths() == ["paths.archive"]


def test_deckel_bei_maximal_fuenf_personen(zwei_profile):
    while len(list_profiles()) < MAX_PROFILE:
        create_profile()

    assert len(list_profiles()) == MAX_PROFILE

    with pytest.raises(RuntimeError, match="Haushalt"):
        create_profile()


def test_der_deckel_gilt_der_anzahl_nicht_der_kennung(zwei_profile):
    # Anlegen und Entfernen treibt die Kennungen hoch. Hinge der Deckel an
    # ihnen, wäre er nach ein paar Runden erreicht, obwohl nur zwei Personen
    # geführt werden.
    for _ in range(6):
        remove_profile(create_profile())

    assert len(list_profiles()) == 2

    neu = create_profile()

    assert int(neu) > MAX_PROFILE
    assert len(list_profiles()) == 3


def test_eine_kennung_wird_nie_wiederverwendet(zwei_profile):
    """Sonst erbte die neue Person den Bestand der entfernten.

    `remove_profile` nimmt nur aus der Liste; der Ordner bleibt liegen.
    """
    erste = create_profile("Zwischendurch")
    (zwei_profile / "profiles" / erste / "archive").mkdir(parents=True)
    (zwei_profile / "profiles" / erste / "archive" / "alt.pdf").write_bytes(b"x")

    remove_profile(erste)
    zweite = create_profile("Danach")

    assert zweite != erste
    assert not (zwei_profile / "profiles" / zweite / "archive").exists()
    # Der Bestand der entfernten Person liegt unangetastet weiter da.
    assert (zwei_profile / "profiles" / erste / "archive" / "alt.pdf").exists()

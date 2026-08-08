"""Profilwechsel und die Sperre dagegen (ADR 015, Schritt 3).

Der gefährlichste Fall dieses Features: ein Wechsel mitten im Stapelimport.
Der Import löst seine Pfade je Dokument neu auf und schriebe den Rest still
in den Bestand der anderen Person.
"""

import sqlite3

import pytest
import yaml

from src.core.app_home import get_app_home, reset_profile_cache
from src.services import background_jobs, import_job
from src.services.profile_service import (
    activate_profile,
    active_profile,
    create_profile,
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
                "paths": {"inbox": "./inbox", "archive": "./archive"},
                "database": {"path": "./database/buerokrator.db"},
                "backup": {"target": "./backups"},
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


def test_wechsel_verschiebt_das_datenverzeichnis(zwei_profile):
    assert active_profile() == "1"
    assert get_app_home() == zwei_profile / "profiles" / "1"

    activate_profile("2")

    assert active_profile() == "2"
    assert get_app_home() == zwei_profile / "profiles" / "2"


def test_unbekanntes_profil_wird_abgelehnt(zwei_profile):
    with pytest.raises(RuntimeError, match="Unbekanntes Profil"):
        activate_profile("99")

    assert active_profile() == "1"


def test_wechsel_auf_das_aktive_profil_tut_nichts(zwei_profile):
    # Auch während eines Imports: es ändert sich ja nichts.
    import_job.start()

    activate_profile("1")

    assert active_profile() == "1"


def test_laufender_import_verhindert_den_wechsel(zwei_profile):
    import_job.start()
    import_job.update_progress(12, 30, "scan.pdf")

    with pytest.raises(RuntimeError, match="Stapel-Import läuft"):
        activate_profile("2")

    # Nichts angefasst: der Import schreibt weiter in denselben Bestand.
    assert active_profile() == "1"
    assert get_app_home() == zwei_profile / "profiles" / "1"


def test_absage_nennt_den_fortschritt(zwei_profile):
    import_job.start()
    import_job.update_progress(12, 30, "scan.pdf")

    with pytest.raises(RuntimeError, match=r"12 von 30"):
        activate_profile("2")


def test_nach_dem_import_geht_der_wechsel_wieder(zwei_profile):
    import_job.start()
    import_job.finish(succeeded=1, duplicates=0, failed=0)

    activate_profile("2")

    assert active_profile() == "2"


def test_abgebrochener_import_blockiert_nicht_dauerhaft(zwei_profile):
    # abort() gibt den Job frei — sonst bliebe der Wechsel für immer gesperrt.
    import_job.start()
    import_job.abort("kaputt")

    activate_profile("2")

    assert active_profile() == "2"


def test_laufender_import_verhindert_das_entfernen(zwei_profile):
    import_job.start()

    # Sonst zöge man dem laufenden Import einen Bestand unter den Füßen weg
    # — und über die Einstellungen wäre die Sperre am Umschalter umgehbar.
    from src.services.profile_service import remove_profile

    with pytest.raises(RuntimeError, match="Stapel-Import läuft"):
        remove_profile("2")


def test_die_datenbank_des_neuen_profils_wird_angelegt(zwei_profile):
    """Beweist, dass das Schema-Flag beim Wechsel zurückgesetzt wird.

    Das Flag gilt pro Prozess. Ohne Reset liefe der erste Zugriff auf das
    zweite Profil an `init_database` vorbei — auf ein Schema ohne Tabellen.
    """
    from src.database.list_documents import list_documents

    # Erst im ersten Profil arbeiten, damit das Flag gesetzt ist.
    assert list_documents() == []

    activate_profile("2")

    # Zweites Profil ist leer: die Datenbank muss hier neu entstehen.
    assert list_documents() == []
    assert (zwei_profile / "profiles" / "2" / "database" / "buerokrator.db").exists()


def test_jobabfrage_ohne_lauf_ist_leer():
    assert background_jobs.is_busy() is False
    assert background_jobs.running_job() is None
    assert background_jobs.describe_running_job() is None


def test_jobabfrage_ohne_gesamtzahl_bleibt_lesbar():
    # Zwischen start() und der ersten Fortschrittsmeldung ist total noch 0 —
    # „(0 von 0)" wäre eine irreführende Angabe.
    import_job.start()

    assert background_jobs.describe_running_job() == "Stapel-Import läuft"

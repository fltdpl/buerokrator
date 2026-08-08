"""Umzug eines Einzelbestands in die Profilstruktur (ADR 015, Schritt 2).

Schwerpunkt sind die Abbruchpfade: der Umzug fasst echte Dokumente an, und
`archive_path` steht absolut in der Datenbank. Ein halber Umzug wäre
schlimmer als gar keiner.
"""

import sqlite3
from pathlib import Path

import pytest
import yaml

from src.core.app_home import get_app_home, get_base_home, reset_profile_cache
from src.services import profile_service
from src.services.profile_service import (
    LEGACY_DIR,
    active_profile,
    enable_profiles,
    list_profiles,
    profiles_enabled,
)

# Vor der conftest-Fixture festhalten (sie leitet aliases_path um).
from src.organizer.issuer_normalizer import aliases_path as _echter_aliases_path
from src.organizer.trash import get_trash_dir as _echter_trash_dir


@pytest.fixture(autouse=True)
def sauberer_profil_cache():
    reset_profile_cache()
    yield
    reset_profile_cache()


@pytest.fixture
def installation(tmp_path, monkeypatch):
    """Einzelnutzer-Installation mit zwei archivierten Dokumenten."""
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text(
        yaml.safe_dump(
            {
                "paths": {
                    "inbox": "./inbox",
                    "archive": "./archive",
                    "exports": "./exports",
                },
                "database": {"path": "./database/buerokrator.db"},
                "backup": {"target": "./backups"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "aussteller_aliase.yaml").write_text(
        "Musterfirma GmbH:\n  - Musterfirma\n", encoding="utf-8"
    )
    (tmp_path / "trash").mkdir()
    (tmp_path / "inbox").mkdir()

    archiv = tmp_path / "archive" / "2026" / "Ausbildung"
    archiv.mkdir(parents=True)

    pfade = []
    for name in ("2004-06-15_Musterschule_Abschlusszeugnis.pdf", "2011-09-30_x.pdf"):
        datei = archiv / name
        datei.write_bytes(b"%PDF-1.4 Testinhalt")
        pfade.append(str(datei))

    # Ein RELATIVER Pfad, wie ihn ältere Importe hinterlassen haben. Der
    # Umzug muss ihn genauso mitnehmen — und er ist die Falle, die den
    # ersten Port am echten Bestand halb kaputt gemacht hat: `Path(...)
    # .exists()` löst relativ gegen das Arbeitsverzeichnis auf und meldete
    # deshalb „vorhanden", solange das alte Archiv noch dort lag.
    relativ = archiv / "2019-03-15_Musterverwaltung_sonstiges.pdf"
    relativ.write_bytes(b"%PDF-1.4 Testinhalt")
    pfade.append(str(relativ.relative_to(tmp_path)))

    db = tmp_path / "database" / "buerokrator.db"
    db.parent.mkdir()
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, archive_path TEXT)")
    conn.executemany(
        "INSERT INTO documents (archive_path) VALUES (?)", [(p,) for p in pfade]
    )
    conn.commit()
    conn.close()

    return tmp_path


def _pfade_in_db(db):
    conn = sqlite3.connect(db)

    try:
        return [row[0] for row in conn.execute("SELECT archive_path FROM documents")]

    finally:
        conn.close()


def test_vorher_gibt_es_keine_profile(installation):
    assert profiles_enabled() is False
    assert list_profiles() == []
    assert get_app_home() == get_base_home()


def test_umzug_verschiebt_bestand_und_zieht_die_pfade_nach(installation):
    bericht = enable_profiles("Person A", "Person B")

    profil = installation / "profiles" / "1"

    assert profiles_enabled() is True
    assert active_profile() == "1"
    assert get_app_home() == profil

    # Dokumente liegen im Profil und die Datenbank zeigt dorthin — auch das
    # mit dem relativen Pfad.
    assert bericht["umgeschrieben"] == 3
    assert bericht["geprueft"] == 3

    for pfad in _pfade_in_db(profil / "database" / "buerokrator.db"):
        assert pfad.startswith(str(profil / "archive"))
        assert Path(pfad).exists()

    assert (profil / "config" / "aussteller_aliase.yaml").exists()
    assert (profil / "trash").exists()


def test_einstellungen_bleiben_in_der_basis(installation):
    enable_profiles()

    assert (installation / "config" / "settings.yaml").exists()
    assert not (installation / "profiles" / "1" / "config" / "settings.yaml").exists()


def test_originale_werden_beiseitegeraeumt_nicht_geloescht(installation):
    enable_profiles()

    beiseite = installation / LEGACY_DIR

    assert (beiseite / "archive" / "2026" / "Ausbildung").exists()
    assert (beiseite / "database" / "buerokrator.db").exists()
    # Am alten Ort liegt nichts mehr, was die App versehentlich benutzen könnte.
    assert not (installation / "archive").exists()
    assert not (installation / "database").exists()


def test_wal_inhalt_geht_nicht_verloren(installation):
    """Der Fall, der eine reine Dateikopie still um Dokumente bringen würde.

    Solange eine zweite Verbindung offen ist, checkpointet SQLite nicht: die
    zuletzt committeten Zeilen stehen dann nur in der -wal-Datei. Genau
    dieser Fehler steckte schon einmal im Backup.
    """
    db = installation / "database" / "buerokrator.db"

    offen = sqlite3.connect(db)
    offen.execute("PRAGMA journal_mode=WAL")
    offen.execute(
        "INSERT INTO documents (archive_path) VALUES (?)",
        (str(installation / "archive" / "2026" / "Ausbildung" / "spaet.pdf"),),
    )
    (installation / "archive" / "2026" / "Ausbildung" / "spaet.pdf").write_bytes(b"x")
    offen.commit()

    try:
        assert db.with_name(db.name + "-wal").exists(), "Aufbau: kein WAL entstanden"

        enable_profiles()

        # 1. Die Kopie kennt die Zeile, die nur im WAL stand.
        profil_db = installation / "profiles" / "1" / "database" / "buerokrator.db"
        assert len(_pfade_in_db(profil_db)) == 4

        # 2. Die Seitendatei ist mit beiseitegeräumt, nicht liegengeblieben.
        beiseite = installation / LEGACY_DIR / "database"
        assert (beiseite / "buerokrator.db").exists()
        assert not (installation / "database").exists()

    finally:
        offen.close()


def test_kein_pfad_bleibt_relativ(installation):
    """Relative Pfade sind arbeitsverzeichnis-abhängig und damit kaputt.

    Genau hier hatte die Gegenprobe eine Lücke: sie prüfte nur, ob die Datei
    existiert — und ein relativer Pfad „existiert" solange, wie der Prozess
    zufällig im alten Basisverzeichnis läuft.
    """
    from pathlib import Path as P

    enable_profiles()

    pfade = _pfade_in_db(
        installation / "profiles" / "1" / "database" / "buerokrator.db"
    )

    assert pfade, "Aufbau: keine Dokumente"
    assert all(P(p).is_absolute() for p in pfade)


def test_gegenprobe_faellt_auf_relative_pfade_nicht_herein(installation, monkeypatch):
    # Ein Pfad, der nach dem Umzug nirgends hinzeigt, muss auffallen —
    # auch wenn das Arbeitsverzeichnis ihn zufällig auflösbar macht.
    import sqlite3 as s

    conn = s.connect(installation / "database" / "buerokrator.db")
    conn.execute(
        "INSERT INTO documents (archive_path) VALUES ('archive/gibt/es/nicht.pdf')"
    )
    conn.commit()
    conn.close()

    monkeypatch.chdir(installation)

    with pytest.raises(RuntimeError, match="nicht am neuen Ort"):
        enable_profiles()

    assert not (installation / "profiles").exists()


def test_kopierte_datenbank_bleibt_nur_fuer_den_besitzer_lesbar(installation):
    # Die Kopie entsteht neu und erbt sonst die umask — sie enthält die
    # OCR-Volltexte aller Dokumente.
    enable_profiles()

    kopie = installation / "profiles" / "1" / "database" / "buerokrator.db"

    assert oct(kopie.stat().st_mode)[-3:] == "600"


def test_zweites_profil_entsteht_leer_und_benannt(installation):
    enable_profiles("Person A", "Person B")

    zweites = installation / "profiles" / "2"

    assert zweites.exists()
    assert not (zweites / "archive").exists()
    assert [p["name"] for p in list_profiles()] == ["Person A", "Person B"]
    assert [p["active"] for p in list_profiles()] == [True, False]


def test_ohne_namen_gibt_es_deutsche_vorbelegungen(installation):
    enable_profiles()

    assert [p["name"] for p in list_profiles()] == ["Benutzer 1", "Benutzer 2"]


def test_zweiter_umzug_wird_abgelehnt(installation):
    enable_profiles()

    with pytest.raises(RuntimeError, match="bereits Profile"):
        enable_profiles()


def test_absoluter_pfad_in_den_einstellungen_verhindert_den_umzug(installation):
    einstellungen = installation / "config" / "settings.yaml"
    inhalt = yaml.safe_load(einstellungen.read_text(encoding="utf-8"))
    inhalt["paths"]["archive"] = "/woanders/archive"
    einstellungen.write_text(yaml.safe_dump(inhalt), encoding="utf-8")

    # Ein absoluter Pfad läge für alle Personen im selben Verzeichnis.
    with pytest.raises(RuntimeError, match="relative Pfade"):
        enable_profiles()

    assert profiles_enabled() is False


def test_fehlende_datei_bricht_ab_und_laesst_alles_stehen(installation, monkeypatch):
    # Gegenprobe simulieren: eine Archivdatei verschwindet zwischen Kopie
    # und Prüfung. Danach muss die Installation unverändert dastehen.
    echte_pruefung = profile_service._pruefe_bestand

    def kaputt(db_path, erwartete_zeilen):
        for pfad in _pfade_in_db(db_path):
            from pathlib import Path

            Path(pfad).unlink()
            break

        return echte_pruefung(db_path, erwartete_zeilen)

    monkeypatch.setattr(profile_service, "_pruefe_bestand", kaputt)

    with pytest.raises(RuntimeError, match="nicht am neuen Ort"):
        enable_profiles()

    assert profiles_enabled() is False
    assert not (installation / "profiles").exists()
    assert not (installation / LEGACY_DIR).exists()
    assert (installation / "database" / "buerokrator.db").exists()
    assert get_app_home() == get_base_home()


def test_reste_eines_abgebrochenen_umzugs_werden_gemeldet(installation):
    (installation / "profiles").mkdir()

    with pytest.raises(RuntimeError, match="existiert bereits"):
        enable_profiles()


def test_datenbank_wird_ueber_die_sqlite_api_kopiert(installation, monkeypatch):
    # Eine reine Dateikopie verlöre im WAL-Modus die zuletzt importierten
    # Dokumente — derselbe Fehler steckte schon einmal im Backup.
    gerufen = []
    echt = profile_service._copy_database

    def merke(source, target):
        gerufen.append(source)
        return echt(source, target)

    monkeypatch.setattr(profile_service, "_copy_database", merke)
    enable_profiles()

    assert len(gerufen) == 1
    assert gerufen[0].name == "buerokrator.db"


def test_feste_pfade_decken_sich_mit_ihren_definitionen(installation):
    # FIXED_ITEMS spiegelt trash und die Alias-Datei. Wandert eine davon,
    # muss die Liste mitwandern — sonst bliebe sie beim Umzug liegen.
    basis = get_base_home()

    assert str(_echter_trash_dir().relative_to(basis)) == profile_service.FIXED_ITEMS[0]
    assert (
        str(_echter_aliases_path().relative_to(basis))
        == profile_service.FIXED_ITEMS[1]
    )

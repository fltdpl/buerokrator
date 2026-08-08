"""Auflösung der Profilebene (ADR 015).

Daten liegen **immer** unter `profiles/<kennung>/`; `profiles.yaml` ist nur
die Verwaltung und darf fehlen. Der Rest der Datei behandelt die Fälle, in
denen sie da, aber unbrauchbar ist — dort wird bewusst laut gescheitert.
"""

import pytest

from src.core import app_home
from src.core.app_home import (
    get_app_home,
    get_base_home,
    reset_profile_cache,
    resolve_path,
)

# Beim Import festhalten: die autouse-Fixture in conftest ersetzt
# issuer_normalizer.aliases_path, sobald ein Test läuft. Testmodule werden
# vorher eingelesen, hier liegt also noch die echte Funktion.
from src.organizer.issuer_normalizer import aliases_path as _echter_aliases_path


@pytest.fixture(autouse=True)
def sauberer_profil_cache():
    reset_profile_cache()
    yield
    reset_profile_cache()


@pytest.fixture
def basis(tmp_path, monkeypatch):
    monkeypatch.setenv("BUEROKRATOR_HOME", str(tmp_path))
    return tmp_path


def _profile_datei(basis, inhalt):
    (basis / app_home.PROFILES_FILE).write_text(inhalt, encoding="utf-8")


def test_ohne_profildatei_gilt_das_standardprofil(basis):
    # Es gibt keine Installation ohne Profil — die Datei ist nur die
    # Verwaltung, nicht die Struktur.
    assert get_base_home() == basis
    assert get_app_home() == basis / "profiles" / "1"
    assert resolve_path("archive") == basis / "profiles" / "1" / "archive"


def test_mit_profil_trennen_sich_basis_und_daten(basis):
    _profile_datei(basis, "active: '1'\n")

    assert get_base_home() == basis
    assert get_app_home() == basis / "profiles" / "1"
    assert resolve_path("archive") == basis / "profiles" / "1" / "archive"


def test_einstellungen_bleiben_in_der_basis_aliase_wandern_mit(basis):
    from src.core.config import config_path

    _profile_datei(basis, "active: '2'\n")
    profil = basis / "profiles" / "2"

    assert config_path() == basis / "config" / "settings.yaml"
    assert _echter_aliases_path() == profil / "config" / "aussteller_aliase.yaml"


def test_log_und_setup_marker_gehoeren_zur_installation(basis):
    from src.services.setup_service import setup_marker_path

    _profile_datei(basis, "active: '2'\n")

    # Der Assistent prüft Ollama/Tesseract — ein zweites Profil darf ihn
    # nicht erneut auslösen.
    assert setup_marker_path().parent == basis


def test_wechsel_der_datei_wird_bemerkt(basis):
    _profile_datei(basis, "active: '1'\n")
    assert get_app_home().name == "1"

    _profile_datei(basis, "active: '22'\n")
    reset_profile_cache()

    assert get_app_home().name == "22"


def test_zweiter_aufruf_parst_nicht_erneut(basis, monkeypatch):
    _profile_datei(basis, "active: '1'\n")
    get_app_home()

    # Ein zweiter Aufruf darf die Datei nicht noch einmal lesen — sonst
    # parst der Stapelimport je Dokument mehrfach YAML.
    def explodiere(*args, **kwargs):
        raise AssertionError("profiles.yaml wurde erneut geparst")

    monkeypatch.setattr(app_home.yaml, "safe_load", explodiere)

    assert get_app_home().name == "1"


@pytest.mark.parametrize(
    "inhalt",
    [
        "",
        "active:\n",
        "active: ''\n",
        "profiles: [1, 2]\n",
        "kein mapping\n",
        "active: [1]\n",
    ],
)
def test_unbrauchbare_profildatei_ist_ein_harter_fehler(basis, inhalt):
    # Kein stiller Rückfall auf das Standardprofil: das öffnete einen
    # fremden oder leeren Bestand und schriebe neue Importe am eigentlichen
    # Bestand vorbei.
    _profile_datei(basis, inhalt)

    with pytest.raises(RuntimeError):
        get_app_home()


@pytest.mark.parametrize(
    "kennung",
    ["../../etc", "..", "/absolut", "eins/zwei", "mit leerzeichen", "punkt.punkt"],
)
def test_kennung_kann_nicht_aus_dem_profilordner_ausbrechen(basis, kennung):
    _profile_datei(basis, f"active: '{kennung}'\n")

    with pytest.raises(RuntimeError):
        get_app_home()


def test_kaputtes_yaml_meldet_sich(basis):
    _profile_datei(basis, "active: '1'\n  offen: [\n")

    with pytest.raises(RuntimeError):
        get_app_home()


def test_zwei_basen_stoeren_sich_nicht(tmp_path, monkeypatch):
    eins = tmp_path / "eins"
    zwei = tmp_path / "zwei"
    eins.mkdir()
    zwei.mkdir()
    _profile_datei(eins, "active: 'a'\n")
    _profile_datei(zwei, "active: 'b'\n")

    monkeypatch.setenv("BUEROKRATOR_HOME", str(eins))
    assert get_app_home() == eins / "profiles" / "a"

    monkeypatch.setenv("BUEROKRATOR_HOME", str(zwei))
    assert get_app_home() == zwei / "profiles" / "b"

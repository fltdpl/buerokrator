"""Globale Test-Fixtures."""

import logging

import pytest


@pytest.fixture(autouse=True, scope="session")
def kein_schreiben_ins_nutzer_log():
    """Kein Test schreibt ins echte Log des Nutzers.

    Im Entwickler-Modus zeigt das App-Home auf das Repo; der Logger hängt also
    an logs/buerokrator.log. Jeder Testlauf hat dort angehängt — auch die
    ERROR-Zeilen der Fehlerpfad-Tests, samt tmp-Pfaden. Beim Diagnostizieren
    waren sie von echten Fehlern nicht zu unterscheiden, und sie füllten die
    2-MB-Rotation mit Rauschen.

    Nur der Datei-Handler wird abgehängt: über die Weitergabe an den
    Root-Logger bleibt caplog unverändert nutzbar.
    """
    from src.core.logger import logger as app_logger

    for handler in list(app_logger.handlers):
        app_logger.removeHandler(handler)
        handler.close()

    app_logger.addHandler(logging.NullHandler())


@pytest.fixture(autouse=True)
def isolierte_aussteller_aliase(tmp_path, monkeypatch):
    """Kein Test liest die echte Alias-Datei des Nutzers.

    Im Entwickler-Modus zeigt das App-Home auf das Repo — ohne Umleitung
    hingen Dateinamen-Tests von der lokalen, nutzergepflegten
    aussteller_aliase.yaml ab. Tests, die Aliase brauchen, schreiben die
    Datei nach tmp_path (derselbe Pfad wie hier).
    """
    from src.organizer import issuer_normalizer

    monkeypatch.setattr(
        issuer_normalizer,
        "aliases_path",
        lambda: tmp_path / "aussteller_aliase.yaml",
    )
    monkeypatch.setattr(
        issuer_normalizer, "_cache", {"key": None, "value": ({}, ())}
    )

"""Globale Test-Fixtures."""

import pytest


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

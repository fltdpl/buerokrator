"""Kein Extraktions-Prompt darf Feldbeschreibungen als Werte anbieten.

Beim Rechnungs-Prompt hat das Modell die rechte Seite von `issuer = ...` als
Wert übernommen (siehe test_invoice_prompt.py). Die anderen Prompts benutzen
dieselbe `- feld = beschreibung`-Schreibweise — also dieselbe Einladung.
Geprüft wird jeder Prompt, der diese Schreibweise verwendet; ein neuer
Prompt fällt damit automatisch unter die Regel.
"""

import re
from pathlib import Path

import pytest

PROMPTS = Path(__file__).resolve().parents[1] / "src" / "classifier" / "prompts"

FELDZEILE = re.compile(r"^-\s*\w+\s*=", re.MULTILINE)


def _prompts_mit_feldbeschreibungen():
    return sorted(
        pfad.name
        for pfad in PROMPTS.glob("extract_*.txt")
        if FELDZEILE.search(pfad.read_text(encoding="utf-8"))
    )


def test_die_schreibweise_ist_ueberhaupt_in_gebrauch():
    # Sonst prüfte der Test unten still gar nichts.
    assert len(_prompts_mit_feldbeschreibungen()) >= 2


@pytest.mark.parametrize("name", _prompts_mit_feldbeschreibungen())
def test_prompt_schliesst_feldbeschreibungen_als_wert_aus(name):
    # Bewusst keine feste Stelle: im Arbeits-Prompt kippte derselbe Satz
    # VOR dem Schema eine Gehaltsabrechnung reproduzierbar zur
    # Lohnsteuerbescheinigung; am Ende, bei den Leer-Regeln, nicht.
    prompt = (PROMPTS / name).read_text(encoding="utf-8")

    assert "nie der Wert" in prompt, (
        f"{name} sagt nicht, dass die Beschreibungen keine Werte sind"
    )

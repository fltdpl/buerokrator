"""Der Rechnungs-Prompt darf nichts anbieten, was das Modell abschreiben kann.

Am Bestand gemessen: mehrere Dokumente trugen als `issuer` die Feldbeschreibung
aus diesem Prompt statt eines Ausstellers — das Modell hat die rechte Seite von
`issuer = ...` als Wert genommen. Gefunden hat es der Tarball-Scan nebenbei,
nicht die Qualitaetsmessung; ein geprueftes Dokument war darunter, der Wert
stand also in der Ground Truth und wanderte in den Dateinamen.

Dieselbe Falle wie bei den Betreff-Beispielen (`test_health.py`) und bei
Few-Shot (ADR 013). Geprueft wird der ZWECK, nicht ein Wortlaut.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROMPT = REPO / "src" / "classifier" / "prompts" / "extract_invoice.txt"


def _prompt():
    return PROMPT.read_text(encoding="utf-8")


def _feldbeschreibungen(prompt):
    """Die rechten Seiten der `- feld = beschreibung`-Zeilen.

    Genau diese Zeichenketten sind im Bestand als Werte aufgetaucht.
    """
    return [
        treffer.group(2).strip()
        for treffer in re.finditer(r"^-\s*(\w+)\s*=\s*(.+)$", prompt, re.MULTILINE)
    ]


def test_prompt_schliesst_feldbeschreibungen_als_wert_aus():
    """Es muss dastehen, dass die Beschreibung selbst nie der Wert ist.

    Ohne diese Regel bleibt die `feld = beschreibung`-Schreibweise eine
    Einladung: sie sieht aus wie eine Zuweisung.
    """
    prompt = _prompt()

    assert _feldbeschreibungen(prompt), "Der Prompt nennt gar keine Felder mehr"
    assert "nie der Wert" in prompt, (
        "Der Prompt sagt nicht, dass die Beschreibungen keine Werte sind"
    )


def test_aussteller_muss_woertlich_aus_dem_dokument_kommen():
    """Der Aussteller wandert in den Dateinamen und in die Ground Truth.

    Deshalb reicht 'nicht die Beschreibung' nicht — es muss positiv dastehen,
    woher der Wert kommt, samt Ausweg fuer den Fall, dass er fehlt.
    """
    prompt = _prompt()
    zeilen = [z for z in prompt.splitlines() if z.strip().startswith("- issuer")]

    assert zeilen, "Der Prompt beschreibt kein issuer-Feld mehr"

    beginn = prompt.index(zeilen[0])
    abschnitt = prompt[beginn : beginn + 400]

    assert "WÖRTLICH" in abschnitt, "Der issuer-Abschnitt verlangt keine woertliche Übernahme"
    assert '""' in abschnitt, "Der issuer-Abschnitt nennt keinen Ausweg für 'nicht gefunden'"

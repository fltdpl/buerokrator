# Betrieb

## Voraussetzungen

- Python (venv: `source ~/venvs/buerokrator/bin/activate`)
- Tesseract (+ Poppler für PDF→Bild)
- Ollama mit dem Modell aus `config/settings.yaml` (aktuell `gemma3:4b`)

## Start

```
python -m src.frontend.main     # GUI: http://localhost:8081
```

Neue Dokumente in `inbox/` legen (die Upload-Funktion tut nur das) und über
die Import-Seite als Stapel verarbeiten — das ist der einzige zuverlässige
Verarbeitungsweg. `main.py` (Live-Watcher) ist Alt-Weg.

## Qualität

- Tests: `python -m pytest -q` (grün halten)
- Nach jeder Prompt-/Regel-Änderung: `python evaluate.py --limit 40`
  als Vergleichslauf

## Backup

Regelmäßige Sicherung:

- archive/
- database/
- exports/

`trash/` enthält gelöschte Original-Dokumente (Papierkorb) — bei Bedarf
mitsichern, gelegentlich manuell leeren.

## Relevante Entscheidungen

- [[002_ollama]]
- [[007_gemma3]]
- [[010_nicegui]]

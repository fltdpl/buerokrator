# Betrieb

## Voraussetzungen

- Python (venv: `source ~/venvs/buerokrator/bin/activate`)
- Tesseract (+ Poppler für PDF→Bild)
- Ollama mit dem Modell aus `config/settings.yaml` (aktuell `gemma3:4b`)

## Start

```
streamlit run app.py            # Bestand (Port 8501)
python -m src.frontend.main     # NiceGUI, in Migration (Port 8081)
```

Beide Oberflächen nutzen dieselben Services und dieselbe Datenbank
(siehe [[10_NiceGUI_Migration]]).

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

`static/pdf/` ist nur ein Anzeige-Cache (Kopien fürs Static Serving) und
braucht kein Backup; Verwaistes wird beim App-Start aufgeräumt.

## Relevante Entscheidungen

- [[002_ollama]]
- [[003_streamlit]]
- [[007_gemma3]]

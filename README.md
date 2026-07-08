# Buerokrator

## Vision

Buerokrator automatisiert die private Dokumentenablage und unterstützt bei der Vorbereitung der jährlichen Steuererklärung.

Neue Dokumente landen in einem Eingangsordner, werden per OCR gelesen, klassifiziert, automatisch umbenannt und archiviert; relevante Informationen werden in einer Datenbank gespeichert und in der App geprüft. Alles läuft lokal — keine Cloud.

## Hauptfunktionen

- Stapel-Import aus dem Inbox-Ordner (Scan-Eingang)
- OCR für Bild- und PDF-Dokumente (Tesseract)
- Dokumentklassifikation (Regeln zuerst, LLM für unklare Fälle)
- Extraktion steuerrelevanter Felder je Dokumenttyp/-subtyp
- Automatische Umbenennung und Archivierung nach Jahr/Kategorie
- Prüf-Workflow in der App (GUI mit PDF-Ansicht neben dem Formular)
- Steuerübersicht pro Jahr mit Absetzbarkeit je Dokument + CSV-Export
- Qualitätsmessung gegen geprüfte Dokumente (`evaluate.py`)
- Vollständig lokaler Betrieb (Ollama, SQLite, Streamlit)

## Schnellstart

```bash
source ~/venvs/buerokrator/bin/activate
streamlit run app.py          # App starten
python -m pytest -q           # Tests
python evaluate.py --limit 40 # Qualitätsmessung
```

Details: [[08_Betrieb]]. Für Entwickler: HANDOVER.md (Projektstand) und AGENT_CONTEXT.md.

## Projektstatus

Pipeline, GUI und Steuerübersicht sind funktionsfähig; laufende Arbeit an
Extraktionsqualität (Messung via `evaluate.py`) — offene Punkte in todo.md.

## Dokumentation

- [[00_Vision]]
- [[01_Architektur]]
- [[02_Datenmodell]]
- [[03_Dokumenttypen]]
- [[04_Lernsystem]] (Konzept, nicht umgesetzt)
- [[05_Steuerlogik]]
- [[06_Ordnerstruktur]]
- [[08_Betrieb]]
- [[09_Decisions]]

## Roadmap

[[roadmap]]

## Externe Abhängigkeiten

### Tesseract OCR

Pfade je Plattform in `config/settings.yaml`. Benötigte Sprachen:

- deu
- eng

### Poppler

Wird für die Umwandlung von PDF-Seiten in Bilder verwendet.
Benötigt für OCR von gescannten PDFs.

### Ollama

Lokales LLM für Klassifikation und Extraktion
(Modell in `config/settings.yaml`, aktuell `gemma3:4b`).

### SQLite

Lokale Datenbank

### Streamlit

Oberfläche (Multipage-App: `app.py` + `pages/`).

## Datenschutz

Persönliche Dokumente werden nicht versioniert.
Folgende Ordner sind von Git ausgeschlossen:

- inbox
- archive
- exports
- examples
- temp
- database (inkl. *.db)
- static (PDF-Anzeige-Cache)
- logs

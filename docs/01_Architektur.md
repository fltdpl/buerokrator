# Architektur

Monolithische Python-Anwendung (siehe [[004_folder_structure]]) mit klarer
Trennung Frontend (NiceGUI) / Services / Kernmodule. Alle Komponenten
laufen lokal, keine externen Dienste.

## Komponenten (`src/`)

### OCR (`src/ocr`)

Extrahiert Text aus PDFs und Bildern (Tesseract, Poppler für PDF→Bild).

### Classifier (`src/classifier`)

Bestimmt den Dokumenttyp zweistufig:

1. **Regeln** (`rule_classifier.py`): gewichtetes Keyword-Scoring, entscheidet
   nur bei eindeutigem Ergebnis.
2. **LLM** (`prompts/classify.txt` über Ollama): alle unklaren Fälle.

Enthält außerdem die **Extraktion** (`document_extractor.py`): typspezifische
Prompts; das Ergebnis wird gegen die Feld-Whitelist in
`src/core/document_fields.py` gefiltert.

### Organizer (`src/organizer`)

Benennt Dateien typabhängig um und archiviert sie nach
`archive/<Jahr>/<Kategorie>/`.

### Database (`src/database`)

SQLite, Tabelle `documents`; Migration läuft automatisch beim ersten Zugriff.

### Services (`src/services`)

Framework-freie Anwendungslogik zwischen GUI und Kernmodulen:
Formular-Schemata je Typ/Subtyp (`form_schema.py`), Listen-Filter und
Papierkorb-Löschen (`document_service.py`), Kennzahlen, Log-Zugriff.
Nur Plain Data rein/raus — ohne GUI testbar.

### Frontend (`src/frontend`, NiceGUI)

Start: `python -m src.frontend.main` (Port 8081, nur localhost).
Dashboard, Dokumentenliste, Detail-/Prüfseite (Formular + PDF⇄OCR-Panel,
Shortcuts), Import, Steuer-Übersicht, Einstellungen mit Log-Ansicht.
Enthält nur Darstellung und Event-Verdrahtung; PDFs kommen über die
Route `/pdf/<id>` direkt aus dem Archiv (siehe [[010_nicegui]]).

### Steuer (`src/tax`)

Jahres-Übersicht und CSV-Export (siehe [[05_Steuerlogik]]).

### Evaluation (`src/evaluation`, `evaluate.py`)

Misst Klassifikations- und Extraktionsqualität gegen die in der App
geprüften Dokumente (Ground Truth).

### Watcher (`src/watcher`, `main.py`)

Alt-Weg (Live-Überwachung der Inbox). Der zuverlässige Pfad ist der
Stapel-Import über die Import-Seite.

## Workflow

Scan
↓
inbox
↓
OCR
↓
Klassifikation (Regeln → LLM)
↓
Extraktion (+ Feld-Whitelist)
↓
Organizer (Umbenennen, Archiv)
↓
Datenbank
↓
GUI: Prüfen/Korrigieren → Steuer-Übersicht

## Relevante Entscheidungen

- [[09_Decisions]]

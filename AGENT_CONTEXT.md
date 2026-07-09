# Projektkontext

Projektname: Buerokrator

## Ziel

Automatische Verarbeitung und Archivierung privater Dokumente mit Fokus auf steuerrelevante Unterlagen.

## Datenschutz

- Alle Daten verbleiben lokal.
- Keine Cloud-Speicherung.
- Keine Übertragung sensibler Dokumente an externe Dienste.

## Technologie-Stack

- Python
- SQLite
- Ollama (Modell konfigurierbar in `config/settings.yaml`: Qwen oder gemma3:4b oder gemma4)
- Tesseract OCR (+ Poppler für PDF→Bild)
- NiceGUI (`src/frontend`, Start: `python -m src.frontend.main`, Port 8081)

## Architektur / Pipeline

`inbox` → OCR (`src/ocr`) → Klassifikation (`src/classifier`: Regel-Vorprüfung vor LLM) →
Extraktion (typspezifische Prompts) → Organizer (Umbenennen/Archivieren, `src/organizer`) →
Datenbank (`src/database`). Steuer-Auswertung in `src/tax`.

GUI klar getrennt: NiceGUI-Frontend (`src/frontend`, nur Darstellung/Events)
über framework-freie Services (`src/services`: Formular-Schemata,
Listen-Filter, Papierkorb-Löschen, Kennzahlen, Log). Löschen verschiebt
Originale nach `trash/`.

Dokumenttypen: `invoice, tax, insurance, pension, bank, housing, unknown`.
Feld-Schemata je Typ/Subtyp zentral in `src/core/document_fields.py` (Whitelist als Sicherheitsnetz).

## Dateinamenskonvention

Datum am Anfang, möglichst vollständig; Aufbau ist **typabhängig** (`src/organizer/filename_builder.py`).

Beispiele:
- Rechnung: `2026-03-11_Amazon_RE-123_42EUR.pdf`
- Lohnsteuerbescheinigung: `2024-12_Arbeitgeber_Lohnsteuerbescheinigung.pdf`
- Gehaltsabrechnung: `2024-03_Arbeitgeber_Gehaltsabrechnung.pdf`

Archivstruktur: `archive/<Jahr>/<Kategorie>/<Dateiname>`.

## Konventionen

- Deutschsprachige Labels und Prompts (`src/classifier/prompts/*.txt`).
- Neue Felder immer in `document_fields.py` **und** im Prompt-Schema ergänzen, sonst werden sie verworfen.
- Geldbeträge werden als Betrag (Magnitude) gespeichert; nur `settlement_amount` behält sein Vorzeichen (Erstattung negativ).
- DB-Migration läuft automatisch beim ersten Zugriff (`database.get_connection`).
- Tests neben jedem Feature; `python -m pytest -q` grün halten (venv: `~/venvs/buerokrator`).

## Entwicklungsprinzipien

- Datenschutz vor Komfort
- Nachvollziehbare Entscheidungen
- Erweiterbare Architektur
- Einfache Bedienung

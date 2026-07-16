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
- Tesseract OCR (+ pypdfium2 für PDF→Bild, reines Python-Wheel)
- NiceGUI (`src/frontend`, Start: `python -m src.frontend.main`, Port 8081)

## Architektur / Pipeline

`inbox` → Dubletten-Prüfung (Inhalts-Hash) → OCR (`src/ocr`) → Klassifikation
(`src/classifier`: Regel-Vorprüfung vor LLM) → Extraktion (typspezifische Prompts) →
regelbasierte Nachbearbeitung (`src/extraction`) → Organizer (Umbenennen/Archivieren,
`src/organizer`) → Datenbank (`src/database`). Steuer-Auswertung in `src/tax`.

Regelparser in `src/extraction` dürfen nur rechnen und beschriftete Werte lesen —
niemals Aussteller, Produktname oder Datum konstant setzen. Die App soll Dokumente
beliebiger Anbieter und (später) mehrerer Nutzer verarbeiten.

GUI klar getrennt: NiceGUI-Frontend (`src/frontend`, nur Darstellung/Events) über framework-freie Services (`src/services`: Formular-Schemata, Listen-Filter, Papierkorb, Kennzahlen, Log, Ollama-Modelle, Backup, Systemstatus). Löschen verschiebt Originale nach `trash/` (nie `unlink` auf Archivdateien). Farben und Layout zentral in `src/frontend/theme.py` und `layout.py`; keine Web-Fonts.

DB-Zugriff über `with open_connection() as conn:` (`src/database/database.py`; WAL, timeout, garantiertes close). DB-Zeilen sind dicts mit Zugriff per Spaltenname (`sqlite3.Row`; Queries liefern `dict(row)`) — nie per Position indexieren.

Dokumenttypen: `invoice, tax, insurance, pension, bank, housing, employment, legal, unknown` — **Typ = Lebensbereich** (Gehaltsabrechnung → employment, nicht tax). Feld-Schemata je Typ/Subtyp zentral in `src/core/document_fields.py` (Whitelist als Sicherheitsnetz). Pro Dokument gibt es ein Steuerrelevanz-Flag (`tax_relevant`, Default aus Typ/Subtyp in `src/tax/tax_relevance.py`); `/steuer` zählt Einkommensdokumente nur, wenn steuerrelevant.

Alle Pfade hängen am App-Home (`src/core/app_home.get_app_home()`: Env `BUEROKRATOR_HOME` → cwd-Devmodus mit vorhandener Config → Benutzer-Datenverzeichnis). Neue Pfade nie relativ zur cwd anlegen; Config-Pfade sind nach `load_config()` bereits absolut.

## Dateinamenskonvention

Datum am Anfang, möglichst vollständig; Aufbau ist **typabhängig** (`src/organizer/filename_builder.py`).

Beispiele:
- Rechnung: `2026-03-11_Amazon_RE-123_42EUR.pdf`
- Lohnsteuerbescheinigung: `2021-01-01_bis_2021-06-30_Arbeitgeber_Lohnsteuerbescheinigung.pdf` (mit Bescheinigungszeitraum; ohne: `2024-12_…`)
- Gehaltsabrechnung: `2021-01-01_bis_2021-01-31_Arbeitgeber_Gehaltsabrechnung.pdf` (Abrechnungszeitraum; Altbestand: `2024-03_…`)

Alle LLM-Werte laufen vor dem Dateinamen-Bau durch str-Coercion und `/`-Ersatz (`filename_builder._clean_name` u. a.).

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

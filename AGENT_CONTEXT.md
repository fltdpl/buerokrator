# Projektkontext

Projektname: Buerokrator

Grundkontext für Agenten. **Aktueller Projektstand, letzter Arbeitsblock und
nächste Schritte stehen in `HANDOVER.md`** (lokal, gitignored), die
Aufgabenliste in `todo.md`, die Langfrist-Sicht in `roadmap.md`.

Neue Session? **Zuerst den Skill `/onboarding` aufrufen** — er nimmt die Lage
per Befehl auf (Doku veraltet zwischen Sessions), führt durch die Dokumente
und endet mit Statusbericht und Vorschlag.

## Ziel

Automatische Verarbeitung und Archivierung privater Dokumente mit Fokus auf steuerrelevante Unterlagen.

## Datenschutz

- Alle Daten verbleiben lokal.
- Keine Cloud-Speicherung.
- Keine Übertragung sensibler Dokumente an externe Dienste.

## Technologie-Stack

- Python
- SQLite
- Ollama (Modell konfigurierbar in `config/settings.yaml`, Standard gemma3:4b) —
  **optional**: ohne Ollama läuft der Import im eingeschränkten Modus
  (Regel-Klassifikation, keine Feld-Extraktion); „Erneut prüfen" und
  `evaluate.py` verweigern dann mit klarer Meldung
- Tesseract OCR (+ pypdfium2 für PDF→Bild, reines Python-Wheel)
- NiceGUI (`src/frontend`, Start: `python -m src.frontend.main`, Port 8081).
  Läuft dort bereits eine Instanz, öffnet ein zweiter Start nur den Browser
  dorthin (Browser-Modus: ein geschlossener Tab beendet die App nicht).
- Packaging: PyInstaller-onedir + Linux-Tarball (`bash packaging/build_linux.sh`).
  Version steht NUR in `src/__init__.py`; Änderungen je Release in `CHANGELOG.md`.
  Ein Windows-Paket ist erklärtes Ziel, aber noch nicht gebaut.

## Architektur / Pipeline

`inbox` → Dubletten-Prüfung (Inhalts-Hash) → Textextraktion (`src/ocr`: digitale
PDFs LAYOUTTREU über pypdfium2-Zeichenpositionen, Scans über Tesseract) →
Klassifikation (`src/classifier`: Regel-Vorprüfung vor LLM) → Extraktion
(typspezifische Prompts) → regelbasierte Nachbearbeitung (`src/extraction`) →
Organizer (Umbenennen/Archivieren, `src/organizer`) → Datenbank (`src/database`,
inkl. FTS5-Volltextindex mit Sync-Triggern). Steuer-Auswertung in `src/tax`
(ELSTER-Anlagen-Mapping mit Ampel/Herleitung, Golden-Master-Abgleich
`tax_check.py` gegen gitignorierte Erwartungsdatei).

Regelparser in `src/extraction` (Bauspar-Auszug, Lohnsteuerbescheinigung,
SV-Meldung, Entgeltnachweis) dürfen nur rechnen und beschriftete Werte lesen —
niemals Aussteller, Produktname oder Datum konstant setzen; bei unbekanntem
Layout `{}`. Die App soll Dokumente beliebiger Anbieter und (später) mehrerer
Nutzer verarbeiten.

GUI klar getrennt: NiceGUI-Frontend (`src/frontend`, nur Darstellung/Events) über framework-freie Services (`src/services`: Formular-Schemata, Listen-Filter, Papierkorb, Kennzahlen, Log, Ollama-Modelle, Backup, Systemstatus). Löschen verschiebt Originale nach `trash/` (nie `unlink` auf Archivdateien). Farben und Layout zentral in `src/frontend/theme.py` und `layout.py`; keine Web-Fonts.

DB-Zugriff über `with open_connection() as conn:` (`src/database/database.py`; WAL, timeout, garantiertes close). DB-Zeilen sind dicts mit Zugriff per Spaltenname (`sqlite3.Row`; Queries liefern `dict(row)`) — nie per Position indexieren.

Dokumenttypen: `invoice, tax, insurance, pension, bank, housing, employment, legal, unknown` — **Typ = Lebensbereich** (Gehaltsabrechnung → employment, nicht tax). Feld-Schemata je Typ/Subtyp zentral in `src/core/document_fields.py` (Whitelist als Sicherheitsnetz). Pro Dokument gibt es ein Steuerrelevanz-Flag (`tax_relevant`, Default aus Typ/Subtyp in `src/tax/tax_relevance.py`) und eine Zweck-Kennzeichnung (`tax_purpose`: werbungskosten/krankheitskosten, nur steuerrelevante Rechnungen, vom Nutzer gesetzt); der Steuer-Tab der Analyse-Seite (`/analyse`; `/steuer` leitet um) zählt in die Anlagen-Summen nur geprüfte + steuerrelevante Dokumente. Zweiter Tab „Einkommen": Jahreseinkommen (Brutto/Steuern/rechnerisches Netto) aus geprüften Lohnsteuerbescheinigungen (`src/services/income_service.py`, SVG-Liniendiagramm ohne Chart-Bibliothek in `src/frontend/chart.py`).

Alle Pfade hängen am App-Home (`src/core/app_home.get_app_home()`: Env `BUEROKRATOR_HOME` → cwd-Devmodus mit vorhandener Config → Benutzer-Datenverzeichnis). Neue Pfade nie relativ zur cwd anlegen; Config-Pfade sind nach `load_config()` bereits absolut.

## Dateinamenskonvention

Datum am Anfang, möglichst vollständig; Aufbau ist **typabhängig** (`src/organizer/filename_builder.py`).

Beispiele:
- Rechnung: `2026-03-11_Musterversand_RE-123_42EUR.pdf`
- Lohnsteuerbescheinigung: `2021-01-01_bis_2021-06-30_Arbeitgeber_Lohnsteuerbescheinigung.pdf` (mit Bescheinigungszeitraum; ohne: `2024-12_…`)
- Gehaltsabrechnung: `2021-01-01_bis_2021-01-31_Arbeitgeber_Gehaltsabrechnung.pdf` (Abrechnungszeitraum; Altbestand: `2024-03_…`)

Alle LLM-Werte laufen durch str-Coercion (`filename_builder._text_value`).
Die Pfadsicherheit sitzt zentral in `filename_builder._safe_filename` (per
`@_sanitized` auf jedem `build_*_filename`): der fertige Name ist garantiert
EINE Pfadkomponente — keine Separatoren, keine unter Windows verbotenen
Zeichen, kein führender Punkt, kein Gerätename, nie leer, max. 255 Bytes.
Feldweise Bereinigung reichte nicht: `document_date`, `tax_year` und `month`
liefen daran vorbei, und `normalize_date` gibt unparsbare Werte roh zurück.

Aussteller-Aliase: nutzerpflegbare Datei `config/aussteller_aliase.yaml` im App-Home (kanonischer Name → Schreibweisen, `*` am Ende = Präfix; gitignored — Anbieternamen sind Nutzerdaten und gehören NIE hartkodiert in den Code). `src/organizer/issuer_normalizer.py` lädt sie mtime-gecacht; angewendet beim Dateinamen-Bau und zentral in `extract_document` auf issuer/employer/insurer. Pflege im Einstellungs-Tab „Aliase" (Text-Editor mit Validierung über `parse_aliases_text`) oder extern. Tests werden per conftest-Fixture von der echten Datei isoliert.

Archivstruktur: `archive/<Jahr>/<Kategorie>/<Dateiname>`.

## Konventionen

- Deutschsprachige Labels und Prompts (`src/classifier/prompts/*.txt`).
- Neue Felder immer in `document_fields.py` **und** im Prompt-Schema ergänzen, sonst werden sie verworfen.
- Geldbeträge werden als Betrag (Magnitude) gespeichert; nur `settlement_amount` behält sein Vorzeichen (Erstattung negativ).
- DB-Migration läuft automatisch beim ersten Zugriff (`database.get_connection`).
- Tests neben jedem Feature; `python -m pytest -q` grün halten (venv: `~/venvs/buerokrator`).
  **Zahlen und Namen in Tests immer erfinden** (Repo ist öffentlich, es gab
  Vorfälle — Lehren in `HANDOVER.md`). `tests/conftest.py` isoliert die
  Aussteller-Alias-Datei; `src.frontend.main` nie auf Modulebene eines
  Testmoduls importieren (verstellt die App-Registrierung der Smoke-Tests).

## Entwicklungsprinzipien

- Datenschutz vor Komfort
- Nachvollziehbare Entscheidungen
- Erweiterbare Architektur
- Einfache Bedienung

# Buerokrator

Buerokrator automatisiert die private Dokumentenablage und unterstützt bei der
Vorbereitung der jährlichen Steuererklärung — **vollständig lokal, ohne Cloud**.

Neue Dokumente landen in einem Eingangsordner, werden per OCR gelesen,
klassifiziert, automatisch umbenannt und archiviert; die relevanten Felder
werden in einer lokalen Datenbank gespeichert und in der App geprüft. Keine
Daten verlassen den Rechner — auch keine Web-Fonts.

> Version 0.1.0 — erste öffentliche Vorabversion.

## Hauptfunktionen

- Stapel-Import aus dem `inbox`-Ordner, inklusive Dubletten-Erkennung
- OCR für Bild- und PDF-Dokumente (Tesseract)
- Dokumentklassifikation (Regeln zuerst, LLM für unklare Fälle)
- Extraktion steuerrelevanter Felder je Dokumenttyp/-subtyp
- Automatische Umbenennung und Archivierung nach `archive/<Jahr>/<Kategorie>/`
- Prüf-Workflow in der App (Formular neben PDF-/OCR-Ansicht,
  Strg+Enter = Speichern & Freigeben & weiter)
- Steuerübersicht pro Jahr mit Absetzbarkeit je Dokument + CSV-Export
- Löschen in den Papierkorb statt endgültig
- Backup von Datenbank + Archiv als ZIP auf Knopfdruck

## Voraussetzungen

Alle Werkzeuge laufen lokal:

- **Python 3.12+**
- **[Ollama](https://ollama.com/)** mit einem Sprachmodell
  (Standard `gemma3:4b`): `ollama pull gemma3:4b`
- **Tesseract OCR** mit den Sprachpaketen `deu` und `eng`
  (Ubuntu/Debian: `sudo apt install tesseract-ocr tesseract-ocr-deu`)
- **pypdfium2** für die Umwandlung gescannter PDF-Seiten in Bilder
  (wird als Python-Paket über `requirements.txt` mitinstalliert)

Der plattformabhängige Pfad zu Tesseract steht in
`config/settings.yaml`. Ob alles verfügbar ist, zeigt in der App
*Einstellungen → Konfiguration → Systemstatus*.

## Installation

```bash
git clone <repo-url> buerokrator
cd buerokrator

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Start

```bash
python -m src.frontend.main      # App unter http://localhost:8081
```

Die Datenbank und die Datenordner werden beim ersten Lauf automatisch angelegt.
Eine Kurzanleitung findest du in der App unter *Anleitung*.

## Entwicklung

```bash
python -m pytest -q              # Testsuite
python evaluate.py --limit 40    # Qualitätsmessung gegen geprüfte Dokumente
```

## Technik

Pipeline: `inbox` → OCR (`src/ocr`) → Klassifikation (`src/classifier`) →
Extraktion → Organizer (`src/organizer`) → Datenbank (`src/database`);
Steuer-Auswertung in `src/tax`. Die Oberfläche (`src/frontend`, NiceGUI)
enthält Darstellung und Event-Verdrahtung; die Fachlogik liegt
framework-frei und getestet in `src/services`, einfache Lesezugriffe gehen
direkt an `src/database`.

Weiterführende Dokumentation liegt im Ordner `docs/`.

## Datenschutz

Persönliche Dokumente werden nicht versioniert. Von Git ausgeschlossen sind
u. a. `inbox/`, `archive/`, `exports/`, `database/`, `trash/`, `backups/` und
`logs/`.

## Lizenz

[MIT](LICENSE)

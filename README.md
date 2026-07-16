# Buerokrator

> In vorbereitung: Version 0.1.0 — erste öffentliche Vorabversion.

Buerokrator automatisiert die private Dokumentenablage und unterstützt bei der
Vorbereitung der jährlichen Steuererklärung — **vollständig lokal, ohne Cloud**.

Neue Dokumente landen in einem Eingangsordner, werden per OCR gelesen,
klassifiziert, automatisch umbenannt und archiviert; die relevanten Felder
werden in einer lokalen Datenbank gespeichert und in der App geprüft. Keine
Daten verlassen den Rechner — auch keine Web-Fonts.

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

## Installation als Desktop-Anwendung (Linux)

Aus dem Release-Tarball (`buerokrator-<version>-linux-<arch>.tar.gz`,
selbst baubar, siehe *Entwicklung*) — installiert ohne root für den
aktuellen Benutzer und legt einen Menüeintrag an:

```bash
tar xzf buerokrator-0.1.0-linux-x86_64.tar.gz
cd buerokrator-0.1.0-linux-x86_64
./install.sh
```

Start über das Anwendungsmenü oder `~/.local/bin/buerokrator` — die App
öffnet sich im Browser. Beim ersten Start führt ein Einrichtungsassistent
durch Systemcheck und Speicherorte. Beenden über
*Einstellungen → Konfiguration → Anwendung → Beenden*.

Tesseract und Ollama (siehe *Voraussetzungen*) bleiben auch beim Paket
Systemvoraussetzungen. Alle Nutzerdaten liegen getrennt vom Programm in
`~/.local/share/buerokrator`; zum Entfernen genügt das Löschen von
`~/.local/opt/buerokrator`, dem Symlink `~/.local/bin/buerokrator` und
dem Menüeintrag `~/.local/share/applications/buerokrator.desktop`.

## Installation aus dem Quellcode

```bash
git clone https://github.com/fltdpl/buerokrator.git
cd buerokrator

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Start (Quellcode)

```bash
python -m src.frontend.main      # App unter http://localhost:8081
```

Datenbank und Datenordner werden automatisch angelegt; bei einer frischen
Instanz startet der Einrichtungsassistent (`/einrichtung`).
Eine Kurzanleitung findest du in der App unter *Anleitung*.

## Entwicklung

```bash
python -m pytest -q              # Testsuite
python evaluate.py --limit 40    # Qualitätsmessung gegen geprüfte Dokumente
bash packaging/build_linux.sh    # Linux-Release-Tarball bauen (dist/)
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

# Architektur

Monolithische Python-Anwendung (siehe [[004_folder_structure]]) mit klarer
Trennung Frontend (NiceGUI) / Services / Kernmodule. Alle Komponenten
laufen lokal, keine externen Dienste.

## Komponenten (`src/`)

### OCR (`src/ocr`)

Extrahiert Text aus PDFs und Bildern. PDFs mit eingebettetem Text werden
**layouttreu** rekonstruiert (`pdf_reader.py`: pypdfium2-Zeichenpositionen,
Zeilen-Clustering per vertikaler Überlappung, Spaltensprünge als
Doppel-Leerzeichen) — bei Formularen stehen Beschriftung und Wert dadurch
wieder auf einer Zeile. Bild-PDFs gehen über Tesseract (pypdfium2 rendert).

### Classifier (`src/classifier`)

Bestimmt den Dokumenttyp zweistufig:

1. **Regeln** (`rule_classifier.py`): gewichtetes Keyword-Scoring, entscheidet
   nur bei eindeutigem Ergebnis.
2. **LLM** (`prompts/classify.txt` über Ollama): alle unklaren Fälle.

Enthält außerdem die **Extraktion** (`document_extractor.py`): typspezifische
Prompts; das Ergebnis wird gegen die Feld-Whitelist in
`src/core/document_fields.py` gefiltert und zum Schluss durch die
Aussteller-Aliase geschickt (siehe Organizer).

### Organizer (`src/organizer`)

Benennt Dateien typabhängig um und archiviert sie nach
`archive/<Jahr>/<Kategorie>/`.

**Aussteller-Aliase** (`issuer_normalizer.py`): vereinheitlicht Schreibweisen
desselben Ausstellers. Die Zuordnung steht NICHT im Code, sondern in der
nutzerpflegbaren Datei `config/aussteller_aliase.yaml` im App-Home (kanonischer
Name → Liste der Schreibweisen, `*` am Ende matcht als Präfix; gitignored —
Anbieternamen sind Nutzerdaten). Geladen wird mtime-gecacht, Änderungen wirken
ohne Neustart; unlesbares YAML ergibt eine leere Zuordnung plus Log-Warnung,
nie einen Import-Abbruch. Angewendet an zwei Stellen: beim Dateinamen-Bau und
zentral in `extract_document` auf `issuer`/`employer`/`insurer` — damit tragen
neue Importe und „Erneut prüfen" direkt den kanonischen Namen. Bestandsdokumente
vereinheitlicht die Bulk-Aktion in der Dokumentenliste.

### Database (`src/database`)

SQLite, Tabelle `documents`; Migration läuft automatisch beim ersten Zugriff.

### Services (`src/services`)

Framework-freie Anwendungslogik zwischen GUI und Kernmodulen:
Formular-Schemata je Typ/Subtyp (`form_schema.py`), Listen-Filter,
Bulk-Aktionen und Neuanalyse (`document_service.py`), Jahreseinkommen aus
geprüften Lohnsteuerbescheinigungen (`income_service.py`), Stapel-Import
(`import_job.py`), Kennzahlen, Backup, Systemstatus, Log-Zugriff.
Nur Plain Data rein/raus — ohne GUI testbar.

### Frontend (`src/frontend`, NiceGUI)

Start: `python -m src.frontend.main` (Port 8081, nur localhost). Läuft dort
schon eine Instanz, öffnet der Start nur den Browser dorthin, statt am
belegten Port zu scheitern (im Browser-Modus beendet ein geschlossener Tab
die App nicht — dafür gibt es den Beenden-Knopf).

Seiten: Dashboard, Dokumentenliste (Filter + Bulk-Aktionen), Detail-/Prüfseite
(Formular + PDF⇄OCR-Panel, Shortcuts), Import (mit Dubletten-Erkennung),
**Analyse** (`/analyse` mit den Tabs „Steuer" und „Einkommen"; `/steuer`
leitet um), Papierkorb, Einrichtung, Einstellungen (Tabs Konfiguration,
Aliase, Papierkorb, Backup, Datenbank, Log).

Enthält nur Darstellung und Event-Verdrahtung; PDFs kommen über die
Route `/pdf/<id>` direkt aus dem Archiv (siehe [[010_nicegui]]).
Layout und Farben zentral in `layout.py` / `theme.py` (siehe [[011_theme]]).
Diagramme baut `chart.py` als Inline-SVG — bewusst ohne Chart-Bibliothek
(NiceGUI bündelt keine; das hielte eine weitere Abhängigkeit vom Bundle fern).
Die Serienfarben stehen in `theme.py` und sind auf Farbfehlsichtigkeit geprüft.

### Steuer (`src/tax`)

Jahres-Übersicht/CSV (`tax_summary.py`), ELSTER-Anlagen-Zuordnung mit
Ampel und Beleg-Herleitung (`elster_mapping.py`), Golden-Master-Abgleich
gegen die abgegebene Erklärung (`elster_check.py` + CLI `tax_check.py` —
ein Hinweis-Werkzeug, kein hartes Abnahme-Kriterium; erklärte Differenzen
werden per `ignoriert` ausgeklammert), Steuerrelevanz (`tax_relevance.py`)
und Zweck-Kennzeichnung (`tax_purpose.py`). Details: [[05_Steuerlogik]].

### Evaluation (`src/evaluation`, `evaluate.py`)

Misst Klassifikations- und Extraktionsqualität gegen die in der App
geprüften Dokumente (Ground Truth).

### Regelparser (`src/extraction`)

Nachbearbeitung der LLM-Extraktion für Formulare, die ein 4B-Modell
nachweislich nicht zuverlässig liest: Es kann die zwölf Sparbeiträge eines
Jahreskontoauszugs nicht summieren und ordnet Betragsspalten um eine Zeile
versetzt zu. Beides ist aus dem Text exakt herleitbar — die Beitragssumme
etwa aus der Bilanz (`Endsaldo - Saldovortrag - Zinsen + Steuern`) statt aus
einer Summe, die schon an einer fehlenden OCR-Zeile scheitert.

**Verbindliche Regeln für jeden Regelparser** (die App soll die Dokumente
beliebiger Nutzer und Anbieter verarbeiten):

1. Nur rechnen und beschriftete Werte lesen. **Niemals konstant setzen, was
   das Dokument identifiziert** — Aussteller, Produktname, Datum. Ein
   Muster, das für einen Anbieter geschrieben wurde, darf einem anderen
   nicht dessen Aussteller ins Archiv schreiben.
2. Anbieterabhängig ist ausschließlich die *Erkennung* des Layouts. Sie
   gehört in eine Datenstruktur (`LAYOUTS`), nicht in die Leselogik.
3. Bei unsicherem Layout `{}` zurückgeben, damit die LLM-Werte stehen
   bleiben. Ein fehlendes Feld kostet einen Prüfklick, ein falsches Feld
   ist eine falsche Tatsache in fremden Daten.
4. `evaluate.py` misst den Bestand eines einzigen Nutzers und kann einen
   Verstoß gegen 1.–3. **nicht bemerken** — im Gegenteil, es belohnt ihn
   mit einer höheren Trefferquote. Vor weiterer Optimierung braucht es
   einen zweiten Datensatz mit Dokumenten anderer Anbieter.

Anbieterunabhängig lesbar sind amtlich normierte Formulare: die
Steuerbescheinigung über Kapitalerträge etwa trägt nach § 45a EStG bei
jeder Bank dieselben Beschriftungen.

Aktuelle Parser: Bauspar-Jahreskontoauszug (`account_statement.py`),
Lohnsteuerbescheinigung (`lohnsteuerbescheinigung.py`, nummerierte Zeilen
3–28), SV-Meldebescheinigung § 25 DEÜV (`sv_meldung.py`, inkl.
Storno+Neuausstellung), Entgeltnachweis (`entgeltnachweis.py`,
SAP-HR-Summenzeilen). Alle arbeiten auf dem layouttreuen Text und
überschreiben die LLM-Werte nur für sicher gelesene Felder.

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
Extraktion (+ Feld-Whitelist, + Aussteller-Aliase)
↓
Organizer (Umbenennen, Archiv)
↓
Datenbank
↓
GUI: Prüfen/Korrigieren → Analyse (Steuer / Einkommen)

## Relevante Entscheidungen

- [[09_Decisions]]

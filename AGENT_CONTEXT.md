# Projektkontext — Buerokrator

Verbindliche Regeln und Konventionen für Agenten. Fachliches steht in `docs/`
und wird hier nur verlinkt, nicht wiederholt.

**Neue Session? Zuerst den Skill `/onboarding`** — er nimmt die Lage per
Befehl auf, führt durch die Dokumente und endet mit Bericht und Vorschlag.

Zweck der App: lokale, datenschutzfreundliche Ablage privater Dokumente und
Vorbereitung der Steuererklärung. Alles offline (Tesseract, pypdfium2, SQLite,
NiceGUI, Ollama optional) — keine Cloud, keine Web-Fonts, kein Update-Check.

## Wo was steht

`README.md` Nutzersicht · **`docs/01_Architektur.md` Pipeline und
Komponenten** · `02` Datenmodell · `03` Dokumenttypen · **`04` Steuerlogik
(maßgeblich, sobald es um Steuer geht)** · `05` Archiv- und
Dateinamenskonvention · `06` nie gebaute Konzepte · `07` Betrieb und
Release-Ablauf · `08` alle ADRs · **`CHANGELOG.md` laufend gepflegt** ·
`roadmap.md`
Langfrist · `HANDOVER.md` Sessionstand und lokale Messwerte (gitignored) ·
`todo.md` Aufgaben (gitignored).

`docs/` ist WIP — **im Zweifel ist der Code maßgeblich.**

## Eiserne Regeln

**Der Nutzer committet und taggt selbst.** Am Ende nur eine Commit-Message
vorschlagen, und zwar **als Datei** `.git/COMMIT_MSG_vorschlag.txt` — beim
Kopieren aus dem Chat ging schon einmal die Betreffzeile verloren. Trotzdem den Text auch noch anzeigen. Der Nutzer
sieht dann nur `git commit -F .git/COMMIT_MSG_vorschlag.txt`.

**Den `CHANGELOG.md` mitpflegen, nicht erst beim Release.** Jede
nutzersichtbare Änderung kommt vor dem Commit-Vorschlag in den Abschnitt
„Unveröffentlicht", neueste zuerst: fettes **Neu:** oder **Behoben:**, dann
Problem und Folge aus Nutzersicht — und, falls Bestandsdokumente nachziehen
müssen, wodurch („beim nächsten Speichern", „über Erneut prüfen"). Rein
interne Änderungen höchstens als schlichter Stichpunkt. Es gelten dieselben
Datenschutzregeln wie für jede getrackte Datei.

**Das Repo ist öffentlich, es gab mehrere Vorfälle.**

- In Code, Tests, Doku, Kommentaren und Commit-Messages **nie** echte
  Beträge, Nummern oder Namen — auch keine Anbieter- oder Arbeitgebernamen,
  die der Nutzer im Chat nennt. Immer erfinden („Musterfirma GmbH"),
  arithmetisch konsistent. Anbieternamen gehören in die gitignorierte
  Alias-Datei, nicht in den Code.
- **Keine Bestandszahlen in getrackte Dateien** — keine Bestandsgröße, keine
  Trefferzahlen einer Messung, keine `evaluate.py`-Prozente, keine
  Dokument-IDs. Daraus ließen sich Umfang und Zusammensetzung der privaten
  Sammlung ableiten. Befunde **qualitativ** formulieren; Zahlen gehören nach
  `HANDOVER.md`/`todo.md`.
- **Auch der Chatverlauf ist eine Veröffentlichung.** Bei Diagnose-Abfragen
  nie `filename`, `archive_path`, `issuer`/`employer`, Beträge oder
  Vertragsnummern roh ausgeben — stattdessen Formen und Kennzahlen
  (`re.sub(r"\d", "N", wert)`, Längen, Ja/Nein, Anzahlen). Dokument-IDs sind
  unbedenklich und die nützlichste Währung für Rückfragen.
- Vor jedem Commit-Vorschlag nach Arbeit mit Echtdokumenten
  `/datenschutz-check`, vor Releases zusätzlich `/privacy-scan`.

**Geprüfte Dokumente (`verified = 1`) sind Ground Truth** der
Qualitätsmessung. Änderungen daran nur über die App, nie per SQL;
Diagnose-Zugriffe read-only (`file:…?mode=ro`).

**Gemeldete Einzel-IDs sind ein Hinweis, kein Befund** — erst das Symptom im
ganzen Bestand suchen. Und eigenen Nullmessungen misstrauen: ein Scan mit
„0 Treffern" kann für den gesuchten Fall blind sein; gegen einen bekannten
Positivfall gegenprüfen, bevor man Entwarnung gibt.

**Offline bleiben:** keine Requests an Dritte, keine neuen Abhängigkeiten ohne
Rückfrage. **Sprache Deutsch**, Erklärungen knapp.

## Konventionen beim Programmieren

- **Pfade** über `src/core/app_home.get_app_home()`, nie relativ zur cwd
  (Config-Pfade sind nach `load_config()` bereits absolut).
- **DB** über `with open_connection() as conn:`; Zeilen per Spaltenname
  lesen, nie per Position. Migration läuft automatisch und versioniert — bei
  Schemaänderung `SCHEMA_VERSION` erhöhen.
- **Typ = Lebensbereich** (Gehaltsabrechnung → employment, nicht tax); der
  Zahlungsaspekt ist das Feld `amount`.
- **Neue Felder** nur über `/neues-feld` — die Whitelist in
  `src/core/document_fields.py` verwirft sie sonst still.
- **Beträge als Magnitude** (nur `settlement_amount` behält sein Vorzeichen),
  Datumsformat `DD.MM.YYYY` in Prompts.
- **Regelparser** (`src/extraction`) lesen nur beschriftete Werte und rechnen;
  sie setzen NIE Aussteller, Produkt oder Datum konstant; unbekanntes Layout
  → `{}`. Vollständige Regeln: `docs/01_Architektur.md`.
- **GUI-Trennung:** Frontend (`src/frontend`) nur Darstellung und
  Event-Verdrahtung, Fachlogik framework-frei in `src/services`; einfache
  Lesezugriffe dürfen direkt an `src/database`. Farben und Layout nur in
  `theme.py` / `layout.py`.
- **Dateinamen:** die Pfadsicherheit sitzt zentral in
  `filename_builder._safe_filename`, NICHT feldweise. Konvention:
  `docs/05_Ordnerstruktur.md`.
- **Löschen** verschiebt nach `trash/`, nie `unlink` auf Archivdateien.
  Dateirechte 0600 für DB, Backups und Logs.
- Deutschsprachige Labels und Prompts (`{{ }}` = literale Braces).

## Tests

`python -m pytest -q` grün halten, Tests neben jedem Feature, **Zahlen und
Namen erfinden**. Zwei Fallstricke, die schon Zeit gekostet haben:

- `tests/conftest.py` leitet die Aussteller-Alias-Datei auf `tmp_path` um —
  ohne diese Fixture hängen Dateinamen-Tests an der echten Nutzerdatei.
- **`src.frontend.main` nie auf Modulebene eines Testmoduls importieren.** Der
  Import legt das Modul in `sys.modules` ab, sodass die `@ui.page`-Dekoratoren
  beim App-Neuaufbau für jeden NACHFOLGENDEN Test nicht mehr laufen — alle
  weiteren Seiten antworten dann mit 404.

## Befehle

```bash
source ~/venvs/buerokrator/bin/activate
python -m pytest -q                 # Testsuite
python -m src.frontend.main         # App auf http://localhost:8081
python -m tools.tax_check <jahr>          # Steuerwerte gegen die eigene Erklärung
python -m tools.evaluate --limit 40       # Qualitätsmessung (braucht Ollama)
bash packaging/build_linux.sh       # Release-Tarball nach dist/
```

Die Version steht **nur** in `src/__init__.py`; der Build liest sie von dort.

**Projekt-Skills** (`.claude/skills/`, lokal): `/onboarding` · `/handover` ·
`/extraktion-debug` · `/neues-feld` · `/datenschutz-check` · `/privacy-scan` —
benutzen statt improvisieren.

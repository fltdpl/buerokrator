# Betrieb

## Voraussetzungen

- Python (venv: `source ~/venvs/buerokrator/bin/activate`)
- Tesseract (+ pypdfium2 für PDF→Bild, Python-Wheel)
- Ollama mit dem Modell aus `config/settings.yaml` (aktuell `gemma3:4b`) —
  optional, ohne läuft der Import ohne Feld-Extraktion

## Start

```
python -m src.frontend.main     # GUI: http://localhost:8081
```

Neue Dokumente in `inbox/` legen (die Upload-Funktion tut nur das) und über
die Import-Seite als Stapel verarbeiten — das ist der einzige zuverlässige
Verarbeitungsweg. `main.py` (Live-Watcher) ist Alt-Weg.

Das Schließen des Browser-Tabs beendet die App nicht (dafür der
Beenden-Knopf in den Einstellungen); ein erneuter Start öffnet dann wieder
die laufende Instanz.

## Dateien im App-Home

Alle Pfade hängen an `src/core/app_home.get_app_home()` (Env
`BUEROKRATOR_HOME` → cwd im Entwickler-Modus → Benutzer-Datenverzeichnis,
unter Linux `~/.local/share/buerokrator`):

- `config/settings.yaml` — Konfiguration (Pfade beim Laden absolutiert)
- `config/aussteller_aliase.yaml` — Aussteller-Aliase, nutzerpflegbar
  (Einstellungen → Aliase); enthält persönliche Anbieternamen, gitignored
- `database/`, `archive/`, `inbox/`, `exports/`, `trash/`, `backups/`
- `logs/` — inkl. `console.log` des gepackten Starts (pro Start neu, 0600)

## Qualität

- Tests: `python -m pytest -q` (grün halten)
- Nach jeder Prompt-/Regel-Änderung: `python evaluate.py --limit 40`
  als Vergleichslauf (braucht Ollama)
- Steuerwerte gegen die eigene Erklärung: `python tax_check.py <jahr>`
  (Erwartungsdatei `tax_expected_<jahr>.yaml`, gitignored)

## Release

1. `CHANGELOG.md` ergänzen und `__version__` in `src/__init__.py` bumpen
   (die Version steht nur dort; der Build liest sie von da).
2. Committen, `git tag vX.Y.Z`, `git push && git push --tags`.
3. `bash packaging/build_linux.sh` → `dist/buerokrator-<v>-linux-<arch>.tar.gz`.
4. E2E-Smoke: Tarball in ein frisches `HOME` entpacken, `install.sh`,
   starten, HTTP-Antwort prüfen, aufräumen.
5. GitHub-Release anlegen (CHANGELOG-Abschnitt als Notes, Tarball als
   Asset) — `gh`-CLI ist auf dem Entwicklungsrechner nicht installiert,
   der Schritt läuft im Browser.

## Backup

Regelmäßige Sicherung (oder Backup-Knopf in den Einstellungen, der
Datenbank + Archiv als ZIP sichert und wiederherstellen kann). Die Datenbank
wird dabei über die SQLite-Backup-API gelesen, nicht als Datei kopiert: im
WAL-Modus stehen frisch committete Dokumente in der `-wal`-Datei, solange
eine Verbindung offen ist — eine Dateikopie hätte sie still ausgelassen.
Zu sichern:

- archive/
- database/
- exports/
- config/ (enthält die Alias-Datei)

`trash/` enthält gelöschte Original-Dokumente (Papierkorb) — bei Bedarf
mitsichern, gelegentlich manuell leeren.

## Relevante Entscheidungen

- [[002_ollama]]
- [[007_gemma3]]
- [[010_nicegui]]
- [[012_kein_update_check]]

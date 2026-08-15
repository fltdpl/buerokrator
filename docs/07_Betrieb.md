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
die Import-Seite als Stapel verarbeiten — das ist der Verarbeitungsweg.
`python main.py` im Repo-Root startet dieselbe App.

Das Schließen des Browser-Tabs beendet die App nicht (dafür der
Beenden-Knopf in den Einstellungen); ein erneuter Start öffnet dann wieder
die laufende Instanz.

## Dateien: zwei Wurzeln

Seit [ADR 015](decisions/015_mehrbenutzer_profile.md) gibt es zwei:
`get_base_home()` für die **Installation**, `get_app_home()` für den
**Datenbestand des aktiven Profils**. Die Basis wird wie bisher aufgelöst
(Env `BUEROKRATOR_HOME` → cwd im Entwickler-Modus → Benutzer-Datenverzeichnis,
unter Linux `~/.local/share/buerokrator`).

Basis — für alle Personen dieselbe:

- `config/settings.yaml` — Konfiguration; **relative** Pfade darin werden
  gegen das Profil absolutiert, ein absoluter Pfad hebt die Trennung auf
- `profiles.yaml` — Verwaltung (Liste + aktives Profil); fehlt, solange es
  nur eine Person gibt
- `logs/` — inkl. `console.log` des gepackten Starts (pro Start neu, 0600)
- `.setup_done`, `.nicegui/`

Profil (`profiles/<kennung>/`) — je Person:

- `profile.yaml` — Anzeigename; fehlt, solange nichts umbenannt wurde
- `config/aussteller_aliase.yaml` — Aussteller-Aliase, nutzerpflegbar
  (Einstellungen → Aliase); enthält persönliche Anbieternamen, gitignored
- `database/`, `archive/`, `inbox/`, `exports/`, `trash/`, `backups/`

Ein Bestand aus der Zeit vor ADR 015 (alles direkt in der Basis) wird
einmalig umgezogen. Die **App erkennt ihn beim Start** an der Datenbank am
alten Ort und leitet auf `/umzug`; die Logik steht in
`services/profile_port.py` und ist während eines laufenden Stapel-Imports
gesperrt. Aus dem Quellcode geht derselbe Umzug mit
`python -m tools.port_to_profiles` — dieses Werkzeug verweigert bei
laufender App (eigener Prozess, es prüft den belegten Port).

Ohne diese Erkennung ist der Fall **still**: die App legt im Profil eine
leere Datenbank an und meldet „0 Dokumente", während der Bestand unberührt
eine Ebene höher liegt.

## Qualität

- Tests: `python -m pytest -q` (grün halten)
- Nach jeder Prompt-/Regel-Änderung: `python -m tools.evaluate --limit 40`
  als Vergleichslauf (braucht Ollama)
- Steuerwerte gegen die eigene Erklärung: `python -m tools.tax_check <jahr>`
  (Erwartungsdatei `tax_expected_<jahr>.yaml`, gitignored)

## Release

1. `CHANGELOG.md` ergänzen und `__version__` in `src/__init__.py` bumpen
   (die Version steht nur dort; der Build liest sie von da).
2. Committen, `git tag vX.Y.Z`, `git push && git push --tags`.
3. `bash packaging/build_linux.sh` → `dist/buerokrator-<v>-linux-<arch>.tar.gz`.
4. E2E-Smoke: Tarball in ein frisches `HOME` entpacken, `install.sh`,
   starten, HTTP-Antwort prüfen, mit `uninstall.sh` wieder aufräumen.
5. Tarball vor dem Upload auf Echtdaten prüfen — Release-Pakete bündeln
   `src/classifier/prompts/*` mit: `tar xzOf <t>.tar.gz | grep -a <marker>`.
6. GitHub-Release anlegen, CHANGELOG-Abschnitt als Notes:
   `gh release create vX.Y.Z --verify-tag --notes "…" <tarball>`.

## Backup

Backups liegen im Profil, sichern also **eine** Person.
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

### Wiederherstellung an einem anderen Ort

Seit Schemastand 7 steht `archive_path` **relativ zum App-Home**
([ADR 017](decisions/017_archivpfad_relativ.md)) — ein Ortswechsel des
ganzen Bestands trägt sich damit von selbst, und der Fall unten entsteht
gar nicht erst. Bestände älterer Stände stellt der erste Start um (Backup
neben der Datenbank inklusive).

Zuvor stand der Pfad absolut, und eine anderswo eingespielte Sicherung war
still unbrauchbar: die Dateien lagen richtig, aber jede Zeile zeigte auf den
Ort von der Sicherungszeit — „PDF-Datei nicht gefunden“ in der
Detailansicht, während alle übrigen Werte stimmten. `restore_backup` bindet
die Dateien deshalb nach dem Auspacken selbst neu an
(`services/archive_repair.py`, über die letzten drei Pfadsegmente
`<jahr>/<kategorie>/<datei>`). Das bleibt nötig für alles, was der
Bezugspunkt nicht heilt — eine Sicherung, deren Dateien anders liegen als
zur Sicherungszeit.

Für Bestände, die den Fehler schon tragen: **Einstellungen → Datenbank →
Archivpfade**, oder `python -m tools.repair_archive_paths` (ohne Argument
Trockenlauf, mit `--schreiben` wird geschrieben; vorher entsteht eine
Sicherung `pre_pfadreparatur_….db`). Findet sich eine Datei nicht, bleibt
die Zeile unverändert — **geraten wird nie**.

## Relevante Entscheidungen

- [002 Ollama](decisions/002_ollama.md)
- [007 Modellwahl](decisions/007_gemma3.md)
- [010 NiceGUI](decisions/010_nicegui.md)
- [012 Kein Update-Check](decisions/012_kein_update_check.md)

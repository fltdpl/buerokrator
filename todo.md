# TODO

## Installierbarkeit / Packaging (aus der Machbarkeits-Bewertung, Juli 2026)

**Vorfrage zuerst klären: Für wen?** Desktop-Einzelplatz-Installer und
Mehrbenutzer-Server (Perspektive laut HANDOVER: Accounts) sind verschiedene
Produkte. Für Desktop: der Plan unten. Für Server: Docker statt Installer.
Erst nach dieser Entscheidung in Schritt 3+ investieren.

- [x] **Schritt 1 — cwd-Entkopplung (15.07.2026)**: `src/core/app_home.py`
      mit `get_app_home()` (Auflösung: `BUEROKRATOR_HOME`-Env → cwd mit
      vorhandener Config = Entwickler-Modus → Benutzer-Datenverzeichnis
      `~/.local/share/buerokrator` bzw. `%APPDATA%`). Config-Pfade werden
      beim Laden zentral absolutiert, beim Speichern relativiert; First-Run
      kopiert die mitgelieferte settings.yaml als Vorlage; Logs/Trash
      App-Home-basiert. Bewusst ohne platformdirs (nur Linux/Windows
      unterstützt). Testsuite läuft unverändert über den cwd-Modus.
- [ ] **Schritt 2 — Poppler loswerden statt bundlen**: `pdf2image`+Poppler
      durch `pypdfium2` ersetzen (BSD/Apache, native Bibliothek als Wheel).
      Eine native Abhängigkeit weniger, GPL-Beilage-Frage entfällt. Danach
      bleibt nur Tesseract (portable Binaries beilegen) + Ollama.
- [ ] **Schritt 3 — First-Run-Assistent** auf Basis `dependency_service`:
      Ollama da? Modell da (`ollama pull`-Anleitung mit Ein-Klick-Link)?
      Wo sollen Archiv/Inbox liegen? Statt Fehlermeldungen beim Import.
- [ ] **Schritt 4 — Bundling**: NiceGUI Native-Mode (`native=True`,
      pywebview) → PyInstaller (NiceGUI-offiziell dokumentiert; Tesseract
      als Daten beilegen, `config/settings.yaml`-Vorlage einpacken —
      `config._TEMPLATE` erwartet sie relativ zum Paket) → Installer
      (Inno Setup für Windows zuerst). `.nicegui`-Storage-Verzeichnis
      ins App-Home umleiten.
- [ ] **Ollama-Entscheidung** (kann bis nach Schritt 3 warten, Option a
      berührt die Architektur nicht): (a) geführte Ollama-Installation
      über den First-Run-Assistenten — risikoarm, Modell bleibt über
      Ollama austauschbar; (b) eingebettetes llama.cpp
      (`llama-cpp-python` + GGUF-Download beim ersten Start) — wirklich
      selbständig, aber GPU-Setup fummeliger. Erst bei echtem
      Verteilungsbedarf auf (b) wechseln.
- [ ] **Flankierend vor Weitergabe an Dritte**:
      - `PRAGMA user_version` in die DB schreiben (Migrationsversionierung,
        bevor fremde Datenbestände existieren) + Auto-Backup vor Migration.
      - Update-Weg festlegen (mindestens Versions-Check beim Start) —
        Installer ohne Updates = veraltete Installationen mit alten Bugs.
      - Code-Signing einplanen (SmartScreen/Gatekeeper; Zertifikat kostet
        Geld) — unsignierte Installer schrecken genau die Zielgruppe ab.
      - **Hardware-Realität dokumentieren/abfedern**: gemma3:4b auf
        CPU-only heißt Minuten pro Dokument. Erwartung im First-Run setzen
        (Zeitschätzung anzeigen), ggf. kleineres Modell als Option.

## Feature-Ideen (unpriorisiert, aus dem Review)

- [ ] ELSTER-Zuordnung: Summen konkreten Anlagen/Zeilen zuordnen
  (Alleinstellungsmerkmal ggü. Paperless).
- [ ] Konfidenz-gesteuertes Prüfen: sichere Dokumente (rule + vollständige
  Pflichtfelder) automatisch freigeben, nur unsichere vorlegen.
- [ ] SQLite FTS5 statt `LIKE` für die Volltextsuche.
- [ ] Fristen/Erinnerungen (Kündigungsfristen, Zahlungsziele) aufs Dashboard.
- [ ] Jahres-Abschluss-Checkliste („für 2025 fehlt: …" aus Vorjahresbestand).
- [ ] Optional (bewusst offen): verschlüsselte Backups (age/gpg) — braucht externe Abhängigkeit, gegen den Offline-/Einfachheits-Anspruch abwägen.

## Anmerkungen zur Einordnung

- Vor weiterer Extraktions-Optimierung bleibt der **zweite Testdatensatz**
  (fremde Anbieter) Voraussetzung — siehe HANDOVER-Vermerk; das Review
  bestätigt die Architektur-Entscheidung Regeln+Whitelist+kleines LLM.

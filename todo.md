# TODO — abgeleitet aus dem externen Review (Juli 2026)

Der Bericht wurde stichprobenartig verifiziert; alle übernommenen Punkte sind
bestätigt oder plausibel. Reihenfolge = Priorität.

## P0 — Sofort (Datenschutz) — ERLEDIGT 13.07.2026

- [x] **Git-Historie bereinigt**: `git filter-repo --invert-paths` für die
      beiden PDFs aus `2831de5`, force-gepusht (main: `912b0f0` → `5c25026`).
      Recovery-Bundle: `~/Projekte/buerokrator-prepurge2.bundle` (Nutzer
      löscht es selbst, wenn alles verifiziert ist).
- [x] README-Claim geprüft: stimmt nach der Bereinigung wieder, keine
      Änderung nötig.
- [x] Gegenprobe: `git log --all -- examples/ inbox/ archive/ database/
      backups/ trash/ "*.zip"` leer; `git rev-list --objects --all` enthält
      keine PDF/ZIP-Blobs mehr; alter Hash `2831de5` nicht mehr auflösbar.
- [ ] **Restrisiko GitHub**: Force-Push entfernt die alten Objekte nicht
      sofort serverseitig (unreferenzierte Objekte/Caches können bleiben,
      bis GitHubs GC läuft). Für harte Löschung GitHub-Support anschreiben
      („remove cached views / unreachable objects for commit 2831de5…").
      Die enthaltenen Nummern/Daten weiterhin als offengelegt betrachten.

## P1 — Korrektheit (stille Betragsfehler) — ERLEDIGT 13.07.2026

- [x] **`normalize_amount`-Tausenderformat**: Muster `-?\d{1,3}(\.\d{3})+`
      wird als Tausenderpunkte behandelt (`"1.234"` → 1234.0); englische
      Dezimalzahlen (`1.23`, `1234.56`) unverändert. Tests in
      `tests/test_amount_utils.py`.
- [x] **Typ-Coercion vor dem Dateinamen-Bau**: neue Helper `_text_value` /
      `_clean_name` (str-Coercion) / `_issuer_name` in `filename_builder`;
      alle Builder umgestellt, `amount` läuft durch `normalize_amount`.
      Tests in `tests/test_filename_hardening.py`.
- [x] **`document_subtype` sanitisiert** (pension/bank/housing über
      `_clean_name`, `/` → `_`); Aussteller ebenfalls pfadsicher.
- [x] `parse_llm_json`: Regex-Fallback auf den ersten `{...}`-Block bei
      Prosa ums JSON. Tests in `tests/test_json_utils.py`.

## P2 — Robustheit — ERLEDIGT 13.07.2026

- [x] **DB-Zugriff gehärtet**: `open_connection()`-Context-Manager
      (garantiertes close), `PRAGMA journal_mode=WAL`, `timeout=10` —
      komplette `src/database`-Schicht + `evaluation/ground_truth` migriert.
- [x] **Import-Job abgesichert**: try/except um den Lauf; neue
      `import_job.abort()` gibt den Job frei und merkt den Fehler, die
      /import-Seite zeigt „Import abgebrochen: …" mit Neustart-Button.
- [x] **Upload-Pfad aus der Config** (`paths.inbox` statt hart `inbox/`).
- [x] **Archiv-Pfad aus der Config**: neues `get_archive_root()`
      (`category_mapper`), genutzt von `document_processor` und
      `rename_document`. (`backup_service` nutzt `Path("archive")` nur als
      ZIP-internen Namen — korrekt so.)
- [x] Trash-Reihenfolge dokumentiert (Datei-zuerst ist gewollt: sichtbarer
      Defekt schlägt unsichtbare Waisen-Datei).
- [x] `ocr_service.py`: Config-Load in Funktion (`_configure_ocr`), toter
      `POPPLER_PATH` entfernt, OCR-Sprache kommt jetzt aus `ocr.language`.

## P3 — UX (Prüf-Workflow) — ERLEDIGT 13.07.2026

- [x] **Dirty-Check im Prüf-Screen**: Rückfrage-Dialog („Ungespeicherte
      Änderungen gehen verloren") vor Escape/Pfeiltasten/←→-Buttons;
      Escape/Pfeile greifen nicht mehr in Eingabefeldern (eigene Tastatur
      mit Standard-ignore), Strg+Enter weiterhin überall.
- [x] **Steuerrelevanz-Checkbox** wird bei Typ-/Subtypwechsel aus dem
      Default neu abgeleitet (vor dem Speichern weiter umschaltbar).
- [x] Textfilter debounced (400 ms, Quasar-`debounce`).
- [x] Status als Text („🟢 Geprüft" / „🟡 Ungeprüft"), Spalte sortierbar.

## P4 — Härtung (Datenschutz at rest)

- [ ] Dateirechte `0600` für DB, Backups, Logs (beim Erzeugen setzen).
- [ ] `RotatingFileHandler` fürs Log; PII aus Log-Zeilen reduzieren
      (Dateinamen enthalten Arbeitgeber/Policennummern; DEBUG loggt die
      komplette LLM-Extraktion).
- [ ] Optional: verschlüsselte Backups (age/gpg) — passt zum Anspruch.
- [ ] `/pdf/{id}` bewusst bewerten: lokal ohne Auth ok (127.0.0.1), aber im
      Hinblick auf Mehrbenutzer-Zukunft notieren.

## P5 — Wartbarkeit

- [ ] Typannotationen schrittweise einführen (Kernmodule zuerst:
      `document_fields`, `amount_utils`, `tax_summary`, DB-Schicht).
- [ ] Config-Schlüssel konsequent nutzen oder entfernen: `classifier.mode`
      (toter Schlüssel), `logging.level`, `paths.*` (siehe P2).
- [ ] Frontend→DB-Direktimporte auflösen (Service-Schicht konsequent) ODER
      den README-Anspruch entsprechend abschwächen.
- [ ] Toten Code entfernen: `POPPLER_PATH`-Rest, leeres `validate_document`,
      doppelter `wait_for_file`-Aufruf, Alt-Entrypoint `main.py` (Watcher)
      klar deprecaten.
- [ ] Fehlerpfad-Tests: OCR schlägt fehl, LLM liefert Prosa/kaputtes JSON.

## Feature-Ideen (unpriorisiert, aus dem Review)

- ELSTER-Zuordnung: Summen konkreten Anlagen/Zeilen zuordnen
  (Alleinstellungsmerkmal ggü. Paperless).
- Konfidenz-gesteuertes Prüfen: sichere Dokumente (rule + vollständige
  Pflichtfelder) automatisch freigeben, nur unsichere vorlegen.
- SQLite FTS5 statt `LIKE` für die Volltextsuche.
- Fristen/Erinnerungen (Kündigungsfristen, Zahlungsziele) aufs Dashboard.
- Jahres-Abschluss-Checkliste („für 2025 fehlt: …" aus Vorjahresbestand).

## Anmerkungen zur Einordnung

- Vor weiterer Extraktions-Optimierung bleibt der **zweite Testdatensatz**
  (fremde Anbieter) Voraussetzung — siehe HANDOVER-Vermerk; das Review
  bestätigt die Architektur-Entscheidung Regeln+Whitelist+kleines LLM.
- HANDOVER sagt „todo.md gibt es nicht mehr" — diese Datei ersetzt das alte
  Format bewusst als priorisierte Review-Abarbeitungsliste; HANDOVER beim
  nächsten Update darauf verweisen.

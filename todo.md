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

## P2 — Robustheit

- [ ] **DB-Zugriff härten**: Connection-Context-Manager (try/finally bzw.
      `contextlib`), `PRAGMA journal_mode=WAL`, `timeout=` beim Connect.
      Schützt gegen „database is locked" (Import-Thread schreibt, UI liest).
- [ ] **Import-Job absichern**: `try/finally` um `import_inbox_documents` in
      `import_page.start_import` — bei Exception `import_job` zurücksetzen
      (`finish([], [], [])` o. Ä.) und den Fehler in der UI anzeigen. Sonst
      blockiert `running=True` jeden weiteren Import bis zum Neustart.
      (Hinweis: die Abschluss-Logik hängt NICHT am Browser-Tab — Eventhandler
      laufen app-global; nur der Fehlerfall ist das Problem.)
- [ ] **Upload-Pfad aus der Config**: `import_page.handle_upload` schreibt
      hart nach `Path("inbox")`, der Stapel-Import liest
      `config["paths"]["inbox"]` — vereinheitlichen (Config gewinnt).
- [ ] **Archiv-Pfad aus der Config**: `document_processor.py` und
      `filename_builder.rename_document` nutzen hart `Path("archive")` statt
      `paths.archive`.
- [ ] Nicht-atomare Trash-Operation dokumentieren oder Reihenfolge drehen
      (erst DB-Eintrag löschen? — abwägen, Notiz in `move_document_to_trash`).
- [ ] `ocr_service.py`: Config-Load von Modulebene in Funktion verschieben
      (Import-Zeit-Crash bei fehlendem Key; steht schon als Altlast im
      HANDOVER).

## P3 — UX (Prüf-Workflow)

- [ ] **Dirty-Check im Prüf-Screen**: Escape/Pfeiltasten/Navigation verwerfen
      ungespeicherte Formularänderungen kommentarlos. Änderungsindikator +
      Rückfrage vor dem Verlassen; Escape sollte nicht mitten im Tippen
      greifen.
- [ ] **Steuerrelevanz-Checkbox bei Typ-/Subtypwechsel neu ableiten**
      (aktuell nur beim Seitenaufbau berechnet).
- [ ] Filter debouncen (aktuell eine DB-Abfrage pro Tastenanschlag).
- [ ] Status zusätzlich als Text (nicht nur 🟢/🟡).

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

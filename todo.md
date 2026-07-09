# TODO

## Offen — als Nächstes
- [ ] **Extraktionsqualität verbessern** (82 % → 91 %, weiter): nächster Cluster sind die Gehaltsabrechnungen 2009/10 (#1–#6, Brutto/Netto/Arbeitgeber), danach Subtyp-Verwechslungen (#27, #41, #42).
- [ ] Ground Truth korrigieren (nur über die App): #39 `opening_balance` = 2401.56 (steht als Saldovortrag im Text), #38 `document_date` = `30.12.2020` statt `30.12.2020)`.
- [ ] **Zweiter Testdatensatz** (andere Anbieter, anonymisiert oder synthetisch) — ohne ihn misst `evaluate.py` nur den Bestand eines Nutzers, siehe Vermerk im HANDOVER. Voraussetzung für alles Weitere Richtung Mehrbenutzerbetrieb.
- [ ] Regelmäßig messen: nach JEDER Prompt-/Regel-Änderung `python evaluate.py --limit 40` als Vergleichslauf.

## Erledigt
- [x] Leere Pflichtfelder beim Prüfen hervorheben (`required` im Formular-Schema, `missing_required_fields`).
- [x] Dubletten-Erkennung beim Import (SHA-256 des Originals, Spalte `content_hash`); Dublette wandert vor OCR/LLM in den Papierkorb und wird verlinkt gemeldet.
- [x] Einstellungen: installierte Ollama-Modelle dynamisch (`model_service`, Fallback wenn Ollama nicht läuft).
- [x] Papierkorb-UI unter `/papierkorb` (Wiederherstellen in die Inbox, Leeren mit Bestätigung).
- [x] Bulk-Aktionen in der Dokumentenliste (Auswahl löschen, umklassifizieren → setzt auf ungeprüft).
- [x] Regelparser für Jahreskontoauszug + Steuerbescheinigung (`src/extraction/`): Salden, Zinsen, Beitragssumme aus der Bilanz. Anbieterneutral — setzen nie Aussteller/Produkt/Datum, schweigen bei unbekanntem Layout.
- [x] Dashboard-Zähler „0 ungeprüft · 1 geprüft": `get_verification_statistics` gab ein Dict zurück, die Aufrufer entpackten die Schlüssel statt der Anzahlen.
- [x] GUI auf NiceGUI umgestellt — Phasen 0–4, `docs/10_NiceGUI_Migration.md`, ADR 010. Start: `python -m src.frontend.main`. Streamlit entfernt.
- [x] „Absetzbar"-Mapping je Dokument nach `insurance_type` (absetzbar / nicht / unklar), CSV-Spalte „Absetzbar". Offen: Altverträge vor 2005 wären anteilig absetzbar.
- [x] Steuer-Übersicht: tax-Beträge aus benannten Feldern (`resolve_document_amount`).
- [x] Papierkorb statt endgültigem Löschen (`trash/`); alter `static/pdf`-Cache entfällt komplett (PDF-Serving über Route).
- [x] docs an Code-Stand angeglichen, ADRs 007–010; nicht Umgesetztes als solches markiert.

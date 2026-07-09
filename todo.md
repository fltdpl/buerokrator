# TODO

## Offen — als Nächstes
- [ ] **Extraktionsqualität verbessern** (82 % → 91 %, weiter): nächster Cluster sind die Gehaltsabrechnungen 2009/10 (#1–#6, Brutto/Netto/Arbeitgeber), danach Subtyp-Verwechslungen (#27, #41, #42).
- [ ] Ground Truth korrigieren (nur über die App): #39 `opening_balance` = 2401.56 (steht als Saldovortrag im Text), #38 `document_date` = `30.12.2020` statt `30.12.2020)`.
- [ ] **Zweiter Testdatensatz** (andere Anbieter, anonymisiert oder synthetisch) — ohne ihn misst `evaluate.py` nur den Bestand eines Nutzers, siehe Vermerk im HANDOVER. Voraussetzung für alles Weitere Richtung Mehrbenutzerbetrieb.
- [ ] Regelmäßig messen: nach JEDER Prompt-/Regel-Änderung `python evaluate.py --limit 40` als Vergleichslauf.

## Offen — zurückgestellt (aus GUI-Migration, siehe `docs/10_NiceGUI_Migration.md`)
- [ ] Leere/unsichere Felder beim Prüfen hervorheben (Formular-Schema trägt schon Feld-Metadaten).
- [ ] Dubletten-Erkennung beim Import.
- [ ] Einstellungen: installierte Ollama-Modelle dynamisch abfragen statt fester Liste.
- [ ] Papierkorb-UI (Wiederherstellen, automatisches Leeren von `trash/`).
- [ ] Bulk-Aktionen in der Dokumentenliste (mehrere löschen/umklassifizieren).

## Erledigt
- [x] Regelparser für Jahreskontoauszug + Steuerbescheinigung (`src/extraction/`): Salden, Zinsen, Beitragssumme aus der Bilanz. Anbieterneutral — setzen nie Aussteller/Produkt/Datum, schweigen bei unbekanntem Layout.
- [x] Dashboard-Zähler „0 ungeprüft · 1 geprüft": `get_verification_statistics` gab ein Dict zurück, die Aufrufer entpackten die Schlüssel statt der Anzahlen.
- [x] GUI auf NiceGUI umgestellt — Phasen 0–4, `docs/10_NiceGUI_Migration.md`, ADR 010. Start: `python -m src.frontend.main`. Streamlit entfernt.
- [x] „Absetzbar"-Mapping je Dokument nach `insurance_type` (absetzbar / nicht / unklar), CSV-Spalte „Absetzbar". Offen: Altverträge vor 2005 wären anteilig absetzbar.
- [x] Steuer-Übersicht: tax-Beträge aus benannten Feldern (`resolve_document_amount`).
- [x] Papierkorb statt endgültigem Löschen (`trash/`); alter `static/pdf`-Cache entfällt komplett (PDF-Serving über Route).
- [x] docs an Code-Stand angeglichen, ADRs 007–010; nicht Umgesetztes als solches markiert.

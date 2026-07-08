# TODO

## Datenpflege (in der App erledigen)


## Qualität
- [ ] Regelmäßig messen: nach jeder Prompt-/Regel-Änderung `python evaluate.py --limit 40` als Vergleichslauf.

## Aus HANDOVER übernommen
- [x] „Absetzbar"-Mapping verfeinern — jetzt je Dokument nach `insurance_type` (absetzbar / nicht / unklar), CSV-Spalte „Absetzbar". Bewusst offen: Altverträge vor 2005 (Lebensversicherung) wären anteilig absetzbar.
- [x] `static/pdf/`-Kopien aufräumen — `src/gui/pdf_cache.py`: Löschen entfernt die Kopie mit, App-Start räumt Verwaiste auf.
- [ ] gui auf NiceGUI umstellen — beschlossen; Plan in `docs/10_NiceGUI_Migration.md` (Phase 0: Service-Schicht herauslösen). UX-Verbesserungen sind dort eingeplant:
  - Phase 0: Papierkorb statt endgültigem Löschen; Import-Ergebnis je Datei
  - Phase 2: Prüfansicht ohne Tabs (PDF ⇄ OCR-Text), Prüf-Fortschritt, ein Freigeben-Weg, Listen-Spalten Betrag/Aussteller, Jahr-Bereichsfilter
  - Phase 3: Steuer-„unklar"-Links, Dashboard-Links, „Jetzt prüfen" nach Import, Log-Ansicht in Einstellungen
  - Nach der Migration: leere Felder hervorheben, Dubletten-Erkennung, Ollama-Modellliste, Papierkorb-UI, Bulk-Aktionen
- [ ] Extraktionsqualität weiter verbessern (nach der GUI-Migration; Restfehler-Cluster siehe HANDOVER)

## Sonstiges
- [x] docs prüfen und überarbeiten — alle Dateien an den Code angeglichen, 07_API.md gelöscht, neue ADRs 007–009; nicht Umgesetztes (Lernsystem, geplante Tabellen, Ideenspeicher) ist als solches markiert.

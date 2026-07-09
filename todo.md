# TODO

## Datenpflege (in der App erledigen)


## Qualität
- [ ] Regelmäßig messen: nach jeder Prompt-/Regel-Änderung `python evaluate.py --limit 40` als Vergleichslauf.

## Aus HANDOVER übernommen
- [x] „Absetzbar"-Mapping verfeinern — jetzt je Dokument nach `insurance_type` (absetzbar / nicht / unklar), CSV-Spalte „Absetzbar". Bewusst offen: Altverträge vor 2005 (Lebensversicherung) wären anteilig absetzbar.
- [x] `static/pdf/`-Kopien aufräumen — `src/gui/pdf_cache.py`: Löschen entfernt die Kopie mit, App-Start räumt Verwaiste auf.
- [x] gui auf NiceGUI umstellen — abgeschlossen (Phasen 0–4, `docs/10_NiceGUI_Migration.md`, ADR 010). Start: `python -m src.frontend.main`. Streamlit ist entfernt.
- [ ] Nach der Migration zurückgestellt (siehe Plan-Doku): leere Felder hervorheben, Dubletten-Erkennung, Ollama-Modellliste dynamisch, Papierkorb-UI, Bulk-Aktionen
- [ ] Extraktionsqualität weiter verbessern (nach der GUI-Migration; Restfehler-Cluster siehe HANDOVER)

## Sonstiges
- [x] docs prüfen und überarbeiten — alle Dateien an den Code angeglichen, 07_API.md gelöscht, neue ADRs 007–009; nicht Umgesetztes (Lernsystem, geplante Tabellen, Ideenspeicher) ist als solches markiert.

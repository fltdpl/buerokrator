# TODO

## Datenpflege (in der App erledigen)


## Qualität
- [ ] Regelmäßig messen: nach jeder Prompt-/Regel-Änderung
      `python evaluate.py --limit 40` als Vergleichslauf.

## Aus HANDOVER übernommen
- [ ] Steuer-Übersicht: tax-Kategorie zeigt 0 € (Beträge liegen in benannten
      Feldern, nicht in `amount`) — Übersicht auf benannte Felder umstellen.
- [ ] „Absetzbar"-Mapping verfeinern (nur Versicherungen ist zu grob).
- [ ] `static/pdf/` und DB-Kopien aufräumen (kein Cleanup vorhanden).
- [ ] tax-Subtyp-Selectbox erhält unbekannte Bestandswerte noch nicht
      (pension schon).

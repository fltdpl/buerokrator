# TODO

## Datenpflege (in der App erledigen)
- [ ] Falsch bzw. uneinheitlich erfasste Bestandsdokumente korrigieren.
      Konvention: Typ = Lebensbereich, Subtypen aus dem kanonischen Vokabular
      (`document_fields.py`). Bekannte Fälle: #9 (Nebenkostenabrechnung →
      housing, Subtyp `nebenkostenabrechnung`), #41 (Subtyp → `contract`),
      #46 (Subtyp → `annual_statement`). Prüfen per `python evaluate.py`
      (Regel-Abweichungen im Report).

## Qualität
- [ ] Extraktionsqualität verbessern (aktuell ~58 % Felder korrekt, v. a.
      pension): Extraktions-Prompts gezielt gegen
      `exports/evaluation_report.json` iterieren; typische Muster sind
      fehlende product_name/policy_number, Datumsformate, Bauspar-Salden.
- [ ] Datumsformate vereinheitlichen (DD.MM.YYYY in allen Prompts) und im
      Evaluations-Vergleich datumstolerant vergleichen.
- [ ] Regelmäßig messen: nach jeder Prompt-/Regel-Änderung
      `python evaluate.py --limit 40` als Vergleichslauf.

## Aus HANDOVER übernommen
- [ ] Steuer-Übersicht: tax-Kategorie zeigt 0 € (Beträge liegen in benannten
      Feldern, nicht in `amount`) — Übersicht auf benannte Felder umstellen.
- [ ] „Absetzbar"-Mapping verfeinern (nur Versicherungen ist zu grob).
- [ ] `static/pdf/` und DB-Kopien aufräumen (kein Cleanup vorhanden).
- [ ] tax-Subtyp-Selectbox erhält unbekannte Bestandswerte noch nicht
      (pension schon).

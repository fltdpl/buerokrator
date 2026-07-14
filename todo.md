# TODO

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

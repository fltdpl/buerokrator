# Entscheidung 017

## Thema

`archive_path` relativ speichern — und wogegen relativ

## Entscheidung (15.08.2026)

`documents.archive_path` steht ab **Schemastand 7** relativ zum
**App-Home** des Profils (`archive/<jahr>/<kategorie>/<datei>`), nicht mehr
absolut. Pfade **außerhalb** des App-Home bleiben absolut.

Die Umstellung sitzt an zwei Stellen und nur dort:

- **Schreiben:** `app_home.store_archive_path()`, angewandt in
  `database.insert_document` und `database.update_document` — an der
  Datenbankgrenze, damit kein Aufrufer sie vergessen kann.
- **Lesen:** unverändert `app_home.resolve_archive_path()`. Die Leser
  wurden am 12.08.2026 bereits darauf umgestellt und mussten für diesen
  Schritt **nicht** angefasst werden.

Bestände älterer Stände migriert `init_database.relativize_archive_paths`
beim Start; vorher entsteht wie bei jeder Migration automatisch ein Backup
neben der Datenbank.

## Begründung

**Der absolute Pfad war die Ursache eines realen Fehlerfalls.** Eine
Sicherung, an einem anderen Ort eingespielt, ließ jedes Altdokument ins
Leere zeigen: alle Datenbankwerte richtig, nur die Datei „nicht gefunden"
— still, ohne Fehlermeldung. Die Reparaturfläche aus 0.3.1 heilt den
Schaden, verhindert ihn aber nicht. Relativ gespeichert wandert der
Bezugspunkt mit dem Bestand, und der Fall entsteht gar nicht erst.

**Vor dem Windows-Paket**, weil die Pfade dort zwangsläufig anders aussehen
(`%APPDATA%`) und dieselbe Rechnung sonst ein zweites Mal anfiele.

### Warum das App-Home und nicht der Archiv-Root

Der naheliegende Bezugspunkt wäre der Archiv-Root gewesen
(`<jahr>/<kategorie>/<datei>`). Drei Gründe sprachen dagegen:

1. **`resolve_path` löst schon gegen das App-Home auf.** Damit bleiben
   sämtliche Leser unverändert — die einzige Alternative hätte jeden von
   ihnen angefasst.
2. **`config.save_config` relativiert die Pfadwerte der Einstellungen nach
   exakt derselben Regel** („innerhalb des App-Home → relativ, sonst
   absolut"). Eine Konvention im Projekt statt zweier.
3. **Der Archiv-Root steht in der Config.** Ihn beim Lesen zu brauchen
   hieße `load_config()` je Dokumentzeile — die Datei wird bei jedem Aufruf
   neu geparst, und `parse_document_row` läuft einmal pro Zeile der
   Trefferliste. Das App-Home hat dagegen einen Cache gegen Zeitstempel.

### Warum Fremdpfade absolut bleiben

Ein bewusst außerhalb des App-Home gewähltes Archiv ist kein Formatproblem,
sondern eine Ortsentscheidung. Relativ gespeichert zeigte es nach dem
nächsten Ortswechsel an eine Stelle, an der nie eine Datei lag.

## Folgen für die Reparatur

`services/archive_repair.py` schreibt ebenfalls die Speicherform — sonst
machte jeder Reparaturlauf die Pfade wieder absolut und nähme dem Bestand
genau die Eigenschaft, um die es hier geht.

Zugleich gilt eine Zeile als **heil, sobald der gespeicherte Wert auf die
richtige Datei zeigt** — gleich ob absolut oder relativ notiert. Nur die
Schreibform zu vergleichen hätte einen Bestand aus einer älteren Fassung
vollständig als „repariert" gemeldet, obwohl keine einzige Datei verloren
war. Die Umstellung auf die Speicherform erledigt die Migration.

Die Fläche bleibt trotzdem nötig: für alles, was ein Ortswechsel nicht
heilt (eine Sicherung, deren Dateien anders liegen als zur Sicherungszeit).

## Bewusst nicht geändert

- **`services/profile_port.py`** schreibt weiter absolute Pfade. Es
  arbeitet an einer 0.2.x-Datenbank (Schemastand 3), deren Pfade durchweg
  absolut sind, und seine Gegenprobe braucht sie eindeutig. In die
  Speicherform bringt sie der nächste Start.
- **Der CSV-Export** zeigt weiter den vollständigen Pfad (er löst jetzt
  auf). In einer Tabelle, die der Nutzer außerhalb der App öffnet, ist nur
  der vollständige Pfad zu gebrauchen.
- **Keine Umbenennung der Spalte.** Sie trägt weiter denselben Namen; was
  darin steht, sagt der Kommentar in `init_database.DOCUMENT_COLUMNS`.

# Migrationsplan: Streamlit → NiceGUI

Status: **abgeschlossen** (Phasen 0–4). NiceGUI ist die einzige GUI;
Streamlit wurde entfernt. Bewusste Abweichungen siehe Paritäts-Notizen unten.

## Ziele

- Echtes Event-Modell statt Rerun: Tastatur-Shortcuts, persistenter
  PDF-Viewer, spürbar schnellere Bedienung.
- **Klare Trennung Frontend/Backend**: Das Frontend enthält nur Darstellung
  und Event-Verdrahtung; alle Logik (Daten holen, validieren, speichern,
  Formular-Schemata) liegt in framework-freien Modulen und ist ohne GUI
  testbar.
- Kernlogik (`src/database`, `src/processor`, `src/tax`, `src/core`,
  `src/classifier`, `src/organizer`) bleibt unverändert.

## Nicht-Ziele

- Kein visuelles Redesign (Funktionsparität zuerst, Politur danach).
- Keine neuen Features während der Migration.
- Keine Mehrbenutzerfähigkeit.

## Bestandsaufnahme (Streamlit heute, ~1.550 Zeilen)

| Seite/Modul | Datei | Inhalt |
|---|---|---|
| Dashboard | `app.py` + `views/dashboard.py` | Kennzahlen, Aufgaben-Block, PDF-Cache-Cleanup |
| Dokumente | `views/documents.py` (316) | Liste (Filter, Suche, Tabelle), Sprung ins Detail |
| Detail/Prüfen | `document_renderer.py` (677) | Tabs, typ-/subtypspezifische Formulare, PDF-Viewer, Speichern/Freigeben/Löschen/Umbenennen, Notizen, Prüf-Workflow |
| Import | `views/import_page.py` (96) | Stapel-Import mit Fortschritt, Upload in Inbox |
| Steuer | `views/tax.py` (159) | Jahresübersicht, Metriken, Expander, CSV-Download |
| Einstellungen | `pages/4_Einstellungen.py` (150) | Config-Formular, Gefahrenzone (Reset) |
| Analyse | `views/analysis_page.py` (25) | Zählwerte (ggf. ins Dashboard integrieren) |

Bereits framework-frei: `tax_summary`, `batch_import` (mit
Progress-Callback), alle `src/database`-Funktionen, `document_fields`,
`document_display`, `pdf_cache`.

## Ziel-Architektur

```
src/
├── services/          NEU: framework-freie Anwendungslogik ("Backend")
│   ├── document_service.py    Zeilen-Parsing, Listen-Filter, Tabellenzeilen,
│   │                          Papierkorb-Löschen
│   ├── form_schema.py         deklarative Formular-Schemata je Typ/Subtyp
│   │                          (Feld, Label, Art: text/amount) + merge_form_values
│   ├── pdf_cache.py           Static-PDF-Kopien (aus src/gui hierher verschoben)
│   └── stats_service.py       Dashboard-/Analyse-Kennzahlen
│
│   (Import: processor/batch_import ist bereits framework-frei und liefert
│    seit Phase 0 Ergebnis je Datei; Einstellungen: core/config genügt —
│    keine Wrapper ohne eigene Logik. Speichern+Whitelist+Umbenennen:
│    database/document_repository.save_document.)
│
├── frontend/          NEU: NiceGUI ("Frontend", nur UI + Events)
│   ├── main.py                App-Start, Routing, Layout/Navigation
│   ├── pages/                 dashboard, documents, document_detail,
│   │                          import_, tax, settings
│   └── components/            pdf_viewer, document_table, flash/toast
│
└── gui/               ALT: Streamlit, bleibt bis Parität erreicht ist
```

Regeln für die Trennung:

- Services nehmen und liefern nur Plain Data (dicts/Listen), kein
  `st.*`/`ui.*`, kein Session-State. Alles per pytest ohne GUI testbar.
- Das Frontend rendert Schemata/Daten und ruft Services in Event-Handlern.
  Keine Fachlogik in Handlern (Faustregel: Handler ≤ ~10 Zeilen).
- Die Formular-Definitionen (heute if/elif über 400 Zeilen im Renderer)
  werden EINMAL deklarativ in `form_schema.py` abgelegt — konsistent mit
  `document_fields.py` (Test erzwingt Deckung mit der Whitelist).

## Phasen

### Phase 0 — Backend herauslösen (ohne NiceGUI, Streamlit läuft weiter)

- [x] `src/services/` anlegen; Logik aus `document_renderer.py` und den
      Views extrahieren (Formular-Schemata, Speichern+Normalisierung,
      Lösch-Ablauf inkl. `pdf_cache`, Listenzeilen-Aufbau mit
      Filtern/Jahren, Einstellungen).
- [x] **Papierkorb statt endgültigem Löschen**: der Lösch-Service verschiebt
      das Archiv-PDF nach `trash/` statt es zu vernichten (heute löscht ein
      Fehlklick ein Original unwiederbringlich). Wiederherstellen-UI später.
- [x] **Import-Ergebnis je Datei**: der Import-Service liefert pro Datei
      erkannten Typ, neuen Namen, Zielordner und Dokument-ID (heute nur
      Anzahlen) — Grundlage für besseres Feedback im Frontend.
- [x] Streamlit-Views auf die Services umstellen (dünner machen) —
      beweist die Schnittstelle, bevor NiceGUI existiert.
- [x] Tests für jeden Service; Schema-Whitelist-Konsistenztest.
- Ergebnis: Verhalten unverändert, Suite grün, GUI-Schicht nur noch Anzeige.

### Phase 1 — NiceGUI-Gerüst (parallel zu Streamlit)

- [x] Abhängigkeit `nicegui` aufnehmen; `src/frontend/main.py` mit Layout,
      Navigation, Routing (`/dokumente`, `/dokumente/<id>`, …), eigener Port
      (z. B. 8081), Start-Kommando dokumentieren.
- [x] Static Serving für Archiv-PDFs direkt über FastAPI
      (`app.add_static_files` bzw. Route auf `archive_path`) — die
      `static/pdf`-Kopien entfallen perspektivisch komplett.
- [x] Dashboard als erste Seite (klein, beweist Services + Layout).

### Phase 2 — Dokumente: Liste + Detail/Prüf-Workflow (der Kern)

- [x] Tabelle (AG-Grid/`ui.table`): Sortierung, Zeilenklick → Detail,
      Filter in Seitenleiste (ohne Nonce-Workarounds); **neue Spalten
      Betrag und Aussteller**; Jahr-Filter als EIN Bereichs-Element
      statt zwei Selectboxen.
- [x] Detailseite **ohne Tabs**: Formular links (aus `form_schema.py`
      generiert), rechts persistentes, **umschaltbares Panel PDF ⇄ OCR-Text**
      (den Text braucht man beim Prüfen genau dann, wenn das PDF schwer
      lesbar ist); Notizen auf der Seite.
- [x] Prüf-Workflow: Speichern & Freigeben → nächstes ungeprüftes;
      **Prüf-Fortschritt anzeigen** („noch 7 ungeprüft");
      **Shortcuts** via `ui.keyboard` (z. B. Strg+Enter = Freigeben+weiter,
      N = nächstes, Esc = zurück zur Liste).
- [x] **Nur ein Freigeben-Weg**, der immer speichert (heute verwirft das
      Popover-„Freigeben" ungespeicherte Formularänderungen).
- [x] Löschen (in den Papierkorb) mit Bestätigungsdialog, Umbenennen.
- Meilenstein: Prüf-Workflow komplett in NiceGUI nutzbar → ab hier reale
  Nutzung dort, Streamlit nur noch Fallback.

### Phase 3 — Restliche Seiten

- [x] Import (Upload → Inbox, Stapel-Import mit Fortschrittsanzeige über
      den vorhandenen Callback); Ergebnis je Datei (Typ, Name, Ziel) und
      danach direkter **„Jetzt prüfen"-Button**.
- [x] Steuer (Metriken, Kategorien, Dokument-Links, CSV-Download);
      die „unklar"-Infobox **verlinkt die betroffenen Dokumente** zum
      Nachpflegen.
- [x] Einstellungen (Formular + Gefahrenzone mit Bestätigungsdialog);
      **Log-Ansicht** (Inhalt aus `logs/` einsehbar, z. B. letzte N Zeilen
      mit Level-Filter).
- [x] Dashboard: „Zuletzt archiviert" **verlinkt** die Dokumente;
      Analyse-Zahlen integriert (Analyse-Seite entfällt).

### Phase 4 — Ablösung

- [x] Paritäts-Check gegen die Bestandsaufnahme oben.
- [x] UI-Smoke-Tests mit dem NiceGUI-pytest-Plugin (Ersatz für `AppTest`).
- [x] Streamlit entfernen: `app.py`, `pages/`, `src/gui/`, Abhängigkeit;
      `src/frontend/main.py` wird der Einstieg.
- [x] Docs nachziehen (01, 08, README, HANDOVER); ADR 010 „NiceGUI statt
      Streamlit" (ersetzt 003).
- [x] `static/pdf`-Mechanik + `pdf_cache.py` entfernen, falls durch
      direktes Static Serving ersetzt.

## Nach der Migration (bewusst zurückgestellt)

- Unsichere/leere Felder beim Prüfen hervorheben (das Formular-Schema wird
  in Phase 0 so angelegt, dass es Feld-Metadaten dafür tragen kann).
- Dubletten-Erkennung beim Import.
- Einstellungen: installierte Ollama-Modelle abfragen statt fester Liste.
- Papierkorb-UI (Wiederherstellen, automatisches Leeren).
- Bulk-Aktionen in der Dokumentenliste.

## Risiken / offene Punkte

- **Session-/URL-State**: `?doc=<id>` wird zu echten Routen; Deep-Links aus
  der Steuer-Übersicht müssen mitziehen.
- **Tabelle**: AG-Grid ist mächtig, aber eigene API — früh in Phase 2
  prototypisch absichern (Sortierung + Zeilenklick genügen uns).
- **Upload**: `ui.upload` verhält sich anders als `st.file_uploader`
  (kein Nonce-Trick mehr nötig — Vorteil).
- **Zwei GUIs während der Migration**: beide nutzen dieselben Services;
  Verhaltensdrift wird über die Service-Tests abgefangen.
- **Evaluate/Pipeline unberührt**: Ollama-/OCR-Teile haben keine
  GUI-Abhängigkeit — kein Risiko aus der Migration.

## Reihenfolge-Begründung

Phase 0 zuerst, weil die Trennung Frontend/Backend das erklärte Ziel ist
und JEDE Zeile daraus beiden GUIs zugutekommt — selbst wenn die Migration
pausiert, bleibt ein sauberer geschnittenes System zurück. Der
Prüf-Workflow kommt als erstes echtes NiceGUI-Stück, weil dort alle drei
Schmerzpunkte (Shortcuts, PDF-Sync, Tempo) sitzen.

## Paritäts-Notizen (bewusste Abweichungen)

- Der Info-Tab mit der Rohansicht aller Felder entfällt — die Detailseite
  zeigt direkt das bearbeitbare Formular (gleiche Felder, gleiche Quelle:
  form_schema.py).
- Notizen werden zusammen mit „Speichern" gespeichert, nicht mehr über
  einen eigenen Button (Roadmap-Punkt „Notizen unabhängig speichern"
  bleibt offen).
- „Freigeben ohne Speichern" gibt es nicht mehr — Freigeben speichert
  immer den Formularstand (beabsichtigt, siehe Phase 2).
- Der Archivpfad wird nicht mehr angezeigt (war im Info-Tab); bei Bedarf
  über Download bzw. Dateinamen ersichtlich.

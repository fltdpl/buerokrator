# Datenmodell

## Tabelle documents

- id — eindeutige ID, in der GUI als Route `/dokumente/<id>` und für das PDF-Serving (`/pdf/<id>`) genutzt
- filename
- archive_path — **relativ zum App-Home** (`archive/<jahr>/<kategorie>/…`,
  Schemastand 7, [ADR 017](decisions/017_archivpfad_relativ.md)); nur ein
  Archiv außerhalb des App-Home steht absolut. Geschrieben über
  `app_home.store_archive_path`, gelesen über `resolve_archive_path` —
  **nie roh**, sonst löst der Wert gegen das Arbeitsverzeichnis auf
- document_type
- extracted_data — JSON, Felder je Typ/Subtyp (siehe unten)
- created_at
- verified — 1 = in der App freigegeben (Ground Truth der Qualitätsmessung;
  Zustände und Übergänge: [Prüfworkflow](09_Pruefworkflow.md))
- document_text — OCR-Text (Eingabe für die Qualitätsmessung)
- notes
- tax_year — eigene Spalte, steuert die Archivstruktur `archive/<Jahr>/…`
- content_hash — SHA-256 des Originals (Dubletten-Erkennung beim Import)
- tax_relevant — 0/1/NULL; NULL = Default aus Typ/Subtyp
  (`src/tax/tax_relevance.py`)
- tax_purpose — steuerlicher Zweck eines Beleg-Dokuments
  (werbungskosten/krankheitskosten/NULL), vom Nutzer gesetzt, nie vom LLM

## Volltextindex documents_fts

FTS5 (external content über `documents`, Trigram-Tokenizer für
Substring-Suche, bm25-Ranking); Trigger halten den Index bei
INSERT/UPDATE/DELETE synchron.

Die Trefferliste zeigt zusätzlich die **Fundstelle** aus `document_text`
(`snippet()`, Spaltenindex 3). Zwei Feinheiten: `snippet()` liefert auch
ohne Treffer in dieser Spalte eine Passage — dann den Textanfang **ohne
Markierung**, weil der Treffer aus Dateiname, Feldern oder Notiz kam; nur
die Markierung belegt einen echten Volltext-Treffer, alles andere wird
verworfen. Und markiert wird mit Steuerzeichen statt mit Markup: der Text
stammt aus fremden PDFs und wird in der Oberfläche zuerst escaped
(`_snippet_html` in `pages/documents.py`), danach wäre echtes Markup im
Rohtext nicht mehr vom unseren zu unterscheiden.

## Tags: tags und document_tags

Zwei Tabellen (Schema v5): `tags` und `document_tags` als n:m-Verknüpfung.

Tags sind **flach** — ein Wert, keine Systematik. Ein erster Entwurf sah
Namensräume vor (`koerper:knie`); er wurde vor der Veröffentlichung
verworfen, weil er ein Problem löst, das erst bei sehr vielen Tags entsteht,
dafür aber schon vor dem **ersten** Tag eine Ordnung verlangt. Gruppieren
ließe sich später ergänzen, ohne zu ändern, wie ein Tag geschrieben wird.

**Zwei Spalten für den Namen:** `name` ist die Schreibweise für die Anzeige,
`key` (casefold) trägt die Eindeutigkeit. „Knie-OP" bleibt „Knie-OP",
trifft aber „knie-op". `COLLATE NOCASE` wäre die naheliegende Alternative
und scheidet aus: es faltet nur ASCII, „Ärzte" und „ärzte" blieben zwei
Tags. `color_index` ist eine **laufende Nummer**, kein Farbwert — welche
Palette daraus wird, weiß allein `frontend/theme.py`.

Tags sind bewusst **kein** Feld in `extracted_data` und laufen an der
Whitelist vorbei: dort steht, was **im** Dokument steht, ein Tag ist, was
der Nutzer **über** das Dokument sagt. Nur so gelten sie für alle
Kategorien, ohne dass jeder Dokumenttyp sie einzeln erlauben muss — und nur
so kann ein Tag Dokumente verschiedener Kategorien zusammenhalten (Befund,
Rechnung und Krankmeldung zu derselben Behandlung).

Die Fremdschlüssel stehen als Absicht in der Definition, greifen aber
nicht: SQLite erzwingt sie nur mit `PRAGMA foreign_keys=ON`, und das setzt
die Anwendung nicht. `delete_document` räumt die Zuordnungen deshalb
ausdrücklich mit ab. Ein Tag ohne Zuordnung bleibt als Vokabel bestehen —
Aufräumen ist eine bewusste Handlung, kein Nebeneffekt des Speicherns.

Normalisierung liegt an einer einzigen Stelle
(`services/tag_service`); die Persistenz normalisiert nichts.

**`documents.tags_text` ist abgeleitet, nicht gepflegt.** Der FTS-Index
hängt an `documents`; Tags liegen in eigenen Tabellen und wären für ihn
unsichtbar. Deshalb schreibt `database/tags.py` bei jeder Zuordnungsänderung
die Namen als Text in diese Spalte — das UPDATE löst die vorhandenen
FTS-Trigger aus, der Index zieht von selbst nach. Das gilt für **jede**
Änderung, auch für Umbenennen, Zusammenführen und Löschen in der
Verwaltung: bliebe sie dort aus, fände die Suche ein Tag unter seinem alten
Namen und unter dem neuen gar nicht. Geschrieben wird die Spalte
ausschließlich dort; wächst `FTS_COLUMNS`, baut `create_fts` den Index neu
(eine Virtual Table lässt sich nicht per ALTER erweitern), und
`backfill_tags_text` trägt Bestandszeilen nach.

**Neue Indexspalten immer HINTEN anhängen.** Die Reihenfolge bestimmt den
Spaltenindex der Fundstelle (`search._SNIPPET_COLUMN`) und die Zuordnung
der bm25-Gewichte; eine Einfügung in der Mitte verschöbe beides still.

## Migration

Automatisch beim ersten Zugriff (`database.get_connection` →
`init_database`, ALTER TABLE für fehlende Spalten) und versioniert:
`SCHEMA_VERSION` in `init_database.py` (`PRAGMA user_version`, aktuell 7).
Bestands-DBs mit älterem Stand bekommen vor der Migration automatisch ein
Backup neben der DB; bei jeder Schemaänderung SCHEMA_VERSION erhöhen.

## Dokumentenschema (`extracted_data`)

Die gültigen Felder sind je Dokumenttyp — bei tax, pension, employment und
housing zusätzlich je `document_subtype` (bei education, health und bank
kategorisiert der Subtyp nur) — zentral in
**`src/core/document_fields.py`** definiert (`ALLOWED_FIELDS` + die
`*_SUBTYPE_FIELDS`-Sätze). Diese Whitelist greift bei Extraktion und
Speichern; alles außerhalb wird verworfen, String-Werte werden getrimmt.
Neue Felder müssen dort **und** im Prompt-Schema ergänzt werden
(Formular-Schemata in `src/services/form_schema.py`).

Konventionen:

- Beträge als Magnitude; nur `settlement_amount` behält sein Vorzeichen
  (Erstattung/Guthaben negativ — genutzt von Einkommensbescheinigung und
  den Wohnen-Abrechnungen).
- Datumsformat DD.MM.YYYY.
- Subtypen werden auf ein kanonisches Vokabular normalisiert
  (`KNOWN_SUBTYPES`, `SUBTYPE_ALIASES`, Fuzzy-Match für LLM-Tippfehler).

Es existiert nur die Tabelle `documents` (plus der FTS-Index). Entworfene,
aber nie gebaute Tabellen stehen im [Ideenspeicher](06_Ideen.md).

## Relevante Entscheidungen

- [001 SQLite](decisions/001_sqlite.md)

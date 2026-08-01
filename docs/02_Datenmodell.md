# Datenmodell

## Tabelle documents

- id — eindeutige ID, in der GUI als Route `/dokumente/<id>` und für das PDF-Serving (`/pdf/<id>`) genutzt
- filename
- archive_path
- document_type
- extracted_data — JSON, Felder je Typ/Subtyp (siehe unten)
- created_at
- verified — 1 = in der App geprüft (Ground Truth der Qualitätsmessung)
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

## Migration

Automatisch beim ersten Zugriff (`database.get_connection` →
`init_database`, ALTER TABLE für fehlende Spalten) und versioniert:
`SCHEMA_VERSION` in `init_database.py` (`PRAGMA user_version`, aktuell 3).
Bestands-DBs mit älterem Stand bekommen vor der Migration automatisch ein
Backup neben der DB; bei jeder Schemaänderung SCHEMA_VERSION erhöhen.

## Dokumentenschema (`extracted_data`)

Die gültigen Felder sind je Dokumenttyp — bei tax, pension, employment und
housing zusätzlich je `document_subtype` — zentral in
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

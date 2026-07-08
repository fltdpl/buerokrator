# Datenmodell

## Tabelle documents (einzige Tabelle)

- id — eindeutige ID, in der GUI als `?doc=<id>` und für `static/pdf/<id>.pdf` genutzt
- filename
- archive_path
- document_type
- extracted_data — JSON, Felder je Typ/Subtyp (siehe unten)
- created_at
- verified — 1 = in der App geprüft (Ground Truth der Qualitätsmessung)
- document_text — OCR-Text (Eingabe für die Qualitätsmessung)
- notes
- tax_year — eigene Spalte, steuert die Archivstruktur `archive/<Jahr>/…`

Migration läuft automatisch (`database.get_connection` → `init_database`,
ALTER TABLE für fehlende Spalten).

## Dokumentenschema (`extracted_data`)

Die gültigen Felder sind je Dokumenttyp — bei tax und pension zusätzlich je
`document_subtype` — zentral in **`src/core/document_fields.py`** definiert
(`ALLOWED_FIELDS`, `TAX_SUBTYPE_FIELDS`, `PENSION_SUBTYPE_FIELDS`). Diese
Whitelist greift bei Extraktion und Speichern; alles außerhalb wird
verworfen. Neue Felder müssen dort **und** im Prompt-Schema ergänzt werden.

Konventionen:

- Beträge als Magnitude; nur `settlement_amount` behält sein Vorzeichen
  (Erstattung negativ).
- Datumsformat DD.MM.YYYY.
- Subtypen werden auf ein kanonisches Vokabular normalisiert
  (`KNOWN_SUBTYPES`, `SUBTYPE_ALIASES`, Fuzzy-Match für LLM-Tippfehler).

## Geplante Tabellen (nicht umgesetzt)

Ideen aus der Konzeptphase — es existiert bisher nur `documents`:

### financial_products

- id, product_type (Rentenversicherung, Bausparvertrag, etc.), provider,
  contract_start, contract_number, monthly_contribution, status

### tax_entries

- id, document_id, category, tax_year, deductible_amount

(Die Steuer-Übersicht wird derzeit zur Laufzeit aus `documents` aggregiert,
siehe `src/tax/tax_summary.py`.)

### learning_rules

- id, pattern, category, confidence

(Siehe [[04_Lernsystem]] — Konzept, nicht umgesetzt.)

## Relevante Entscheidungen

- [[001_sqlite]]

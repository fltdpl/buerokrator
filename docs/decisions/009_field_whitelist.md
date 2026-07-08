# Entscheidung 009

## Thema

Feld-Whitelist als Sicherheitsnetz gegen erfundene LLM-Felder

Die gültigen Felder je Dokumenttyp — bei tax und pension je Subtyp — sind
zentral in `src/core/document_fields.py` definiert. Die Whitelist greift
bei der Extraktion **und** beim Speichern aus der GUI; alles außerhalb wird
verworfen. Subtypen werden dabei auf ein kanonisches Vokabular normalisiert
(Aliasse + Fuzzy-Match für LLM-Tippfehler).

Konsequenz: Neue Felder müssen immer in `document_fields.py` **und** im
Prompt-Schema ergänzt werden, sonst werden sie verworfen.

## Begründung

- LLMs erfinden sonst Felder, die unbemerkt in der Datenbank landen
- Ein zentrales Schema hält Prompts, GUI-Formulare und DB konsistent
- Subtypspezifische Feldsätze verhindern irreführende Werte (z. B. keine
  `policy_number` an der aggregierten Steuerbescheinigung)

## Status

Akzeptiert

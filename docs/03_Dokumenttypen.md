# Dokumenttypen

Maßgeblich ist der Code: `src/core/document_types.py` (Typen, gespiegelt in
`config/settings.yaml`) und `src/core/document_fields.py` (Subtypen und ihre
Feldsätze).

## Typen

- invoice
- tax (nur noch Finanzamt-Dokumente; Lohn/Gehalt siehe employment)
- insurance
- pension (inkl. Bausparen — kein eigener Typ)
- bank
- housing
- employment (Arbeit: Verträge, Kündigungen, Zeugnisse, Lohnsteuer/Gehalt,
  SV-Meldungen)
- legal (Recht: Anwalt/Gericht/Behörde; Korrespondenzpartner + Betreff)
- unknown (mit Freitext-Betreff)

**Konvention: Typ = Lebensbereich.** Eine Nebenkostenabrechnung ist
`housing`, nicht `invoice`; der Zahlungsaspekt ist das Feld `amount`.

## Kanonische Subtypen (`document_subtype`)

Nur diese fünf Typen kennen Subtypen (`KNOWN_SUBTYPES`); bei den übrigen
gilt der Feldsatz des Typs.

- **employment**: arbeitsvertrag, kuendigung, arbeitszeugnis,
  lohnsteuerbescheinigung, gehaltsabrechnung, sv_meldung, sonstiges
- **tax**: einkommensbescheinigung, bescheinigung
- **pension**: contract, annual_statement, cost_statement,
  surrender_value_table, pension_information, bauspar_jahresauszug,
  steuerbescheinigung
- **housing**: nebenkostenabrechnung, heizkostenabrechnung, mietvertrag,
  mieterhoehung, hausgeldabrechnung, sonstiges
- **bank**: kontoauszug, kreditkartenabrechnung, depotuebersicht, sonstiges

Frei eingegebene oder vom Modell erfundene Subtypen werden über
`SUBTYPE_ALIASES` und einen Fuzzy-Match auf dieses Vokabular normalisiert
(`normalize_subtype`).

**Altlast bei tax:** `lohnsteuerbescheinigung` und `gehaltsabrechnung` sind
nach employment umgezogen (Aussteller = Arbeitgeber, also Arbeits- und nicht
Steuer-Lebensbereich). In `TAX_SUBTYPE_FIELDS` stehen sie weiterhin — nicht
mehr als Formular, sondern nur noch als Whitelist, damit noch nicht
umsortierte Bestandsdokumente beim Speichern keine Felder verlieren.

## Feldsätze

Welche Felder je Typ/Subtyp gültig sind, steht zentral in
`src/core/document_fields.py` und wirkt als Whitelist bei Extraktion **und**
Speichern. Neue Felder nur über die Checkliste des `/neues-feld`-Skills —
sonst verwirft die Whitelist sie still. Siehe
[Datenmodell](02_Datenmodell.md).

## Nicht umgesetzt

Die Sammlung möglicher Papierarten aus der Konzeptphase steht in
[Ideenspeicher](06_Ideen.md).

# Steuerlogik

Implementiert in `src/tax/tax_summary.py`; GUI-Seite „Steuer".

## Kategorien der Übersicht

Jeder Dokumenttyp wird einer Übersichtskategorie zugeordnet
(`TAX_CATEGORY_BY_TYPE`):

- insurance → Vorsorgeaufwendungen (Sonderausgaben)
- pension → Altersvorsorge & Vermögensaufbau
- tax → Einkommen & Lohnsteuer
- housing → Wohnen
- invoice → Rechnungen
- bank → Bank
- unknown → Sonstiges

## Betrag je Dokument

Grundlage ist das generische Feld `amount`. tax-Dokumente haben keins —
dort greift je Subtyp ein benanntes Feld (`resolve_document_amount`):

- lohnsteuerbescheinigung → income_tax
- einkommensbescheinigung → settlement_amount (Erstattung negativ),
  sonst income_tax
- gehaltsabrechnung → net_amount, sonst gross_amount
- bescheinigung → kein Betrag

## Absetzbarkeit

Wird **je Dokument** entschieden (`document_deductibility`), nicht pauschal
je Kategorie. Für Versicherungen per Keyword auf `insurance_type`:

- **absetzbar**: Kranken, Pflege, Haftpflicht, Unfall,
  Berufsunfähigkeit, Risikoleben, Arbeitslosen (Vorsorge-Keywords gewinnen,
  damit z. B. „Lebensversicherung – BU-Zusatz" über den Vorsorge-Anteil zählt)
- **nicht absetzbar**: Hausrat, Rechtsschutz, Gebäude, Kasko, Reise,
  Kapital-Lebensversicherung
- **unklar**: unbekannte oder fehlende Versicherungsart — der Betrag wird
  separat ausgewiesen statt still mitsummiert

Bewusste Vereinfachung: Lebensversicherungs-Altverträge (vor 2005) wären
anteilig absetzbar; das bleibt außen vor.

Ungeprüfte Beträge werden getrennt von geprüften summiert, damit
unkontrollierte LLM-Zahlen die Summen nicht verfälschen.

## Weitere Summen

- **Gezahlte Lohn-/Einkommensteuer**: Summe `income_tax` über alle Dokumente
  des Jahres.
- **Kapitalerträge (Anlage KAP)**: NUR aus pension-Subtyp
  `steuerbescheinigung` (aggregiert je Anbieter); Bauspar-Jahresauszüge
  würden sonst doppelt zählen.

## Export

Jährlicher CSV-Export, eine Zeile je Dokument, Trennzeichen `;`:

- Datum
- Kategorie
- Betrag
- Absetzbar (ja/nein/unklar)
- Geprueft (ja/nein)
- Dokumentreferenz

## Ausbauideen (nicht umgesetzt)

Feinere steuerliche Kategorien: Werbungskosten, Spenden,
Handwerkerleistungen, Gesundheitskosten (dafür fehlen bisher passende
Dokumenttypen, siehe Ideenspeicher in [[03_Dokumenttypen]]).

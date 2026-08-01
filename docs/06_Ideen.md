# Ideenspeicher

**Kein Ist-Stand.** Hier steht, was einmal gedacht, aber nicht gebaut wurde:
Brainstorming aus der Konzeptphase und Schemaentwürfe, die nie Code geworden
sind. Was tatsächlich existiert, steht in [Dokumenttypen](03_Dokumenttypen.md)
und [Datenmodell](02_Datenmodell.md); was konkret geplant ist, in
`roadmap.md`.

## Geplante Tabellen (nie umgesetzt)

Es existiert bisher nur `documents`. Die Steuer-Übersicht wird zur Laufzeit
daraus aggregiert (`src/tax/tax_summary.py`), Lernregeln gibt es nicht.

### financial_products

- id, product_type (Rentenversicherung, Bausparvertrag, etc.), provider,
  contract_start, contract_number, monthly_contribution, status

### tax_entries

- id, document_id, category, tax_year, deductible_amount

### learning_rules

- id, pattern, category, confidence

Gehört zum Lernsystem (siehe unten).

## Lernsystem aus Benutzerkorrekturen

Das System sollte aus Korrekturen lernen: aus „Vorschlag Gesundheit →
Benutzer wählt Versicherung" würde eine Regel „Zusatzversicherung →
Versicherung". Lernquellen wären Dateiname, Absender, Dokumenttyp und
Benutzerfeedback gewesen.

**Nicht umgesetzt** — es gibt weder Code noch die Tabelle `learning_rules`.
Was dem Ziel am nächsten kommt: die Benutzerkorrekturen aus dem
Prüf-Workflow sind die Ground Truth der Qualitätsmessung (`evaluate.py`).
Verbesserungen fließen daraus **manuell** in Prompts und Regel-Klassifikator
zurück, nicht automatisch.

Ebenfalls nur angedacht war eine Einordnung von Finanzprodukten nach
kurzfristiger steuerlicher Relevanz, langfristiger Vermögensbindung und
reinen Informationsdokumenten.

## Mögliche Dokumenttypen

Diese Liste ist eine Sammlung von Papierarten, die in einem privaten Haushalt
anfallen. Sie ist bewusst breiter als das umgesetzte Typ-Vokabular: dort gilt
**Typ = Lebensbereich**, hier stehen die einzelnen Schriftstücke, die in so
einen Lebensbereich fallen können.

### Arbeit

- [ ] Arbeitsvertrag
- [ ] Änderungsverträge
- [ ] Tarifinformationen
- [ ] Gehaltsmitteilungen
- [ ] Arbeitszeugnisse
- [ ] Fortbildungsnachweise
- [ ] Sozialversicherungsmeldungen
- [ ] Arbeitgeberbescheinigungen
- [ ] Bescheinigungen für Behörden
- [ ] Arbeitszeitnachweise

### Steuern

- [ ] Lohnsteuerbescheinigung
- [ ] Einkommensteuerbescheid
- [ ] Kirchensteuerbescheid
- [ ] Solidaritätszuschlag
- [ ] Vorauszahlungsbescheide
- [ ] ELSTER-Unterlagen
- [ ] Steuerliche Bescheinigungen
- [ ] Spendenbescheinigungen
- [ ] Bescheinigungen für außergewöhnliche Belastungen

### Bank

- [ ] Kontoauszüge
- [ ] Kreditkartenabrechnungen
- [ ] Tagesgeldkonto-Unterlagen
- [ ] Festgeldkonto-Unterlagen
- [ ] Depotunterlagen
- [ ] Wertpapierabrechnungen
- [ ] Darlehensunterlagen
- [ ] Kreditunterlagen
- [ ] Kontoeröffnungen
- [ ] Vertragsänderungen

### Wohnen

- [ ] Mietvertrag
- [ ] Vertragsänderungen
- [ ] Mieterhöhungen
- [ ] Nebenkostenabrechnungen
- [ ] Hausgeldabrechnungen
- [ ] Schriftverkehr mit Vermietern
- [ ] Wohnungsübergabeprotokolle
- [ ] Grundsteuerbescheide
- [ ] Energieausweise
- [ ] Handwerkerrechnungen für Wohneigentum

### Gesundheit

- [ ] Arztrechnungen
- [ ] Zahnarztrechnungen
- [ ] Krankenhausrechnungen
- [ ] Rezepte
- [ ] Heil- und Kostenpläne
- [ ] Leistungsabrechnungen
- [ ] Bonusprogramme
- [ ] Gesundheitsbescheinigungen
- [ ] Impfbescheinigungen
- [ ] Pflegeunterlagen

### Versicherungen

Versicherungsarten: Haftpflicht, Hausrat, Rechtsschutz, Unfall, Kfz,
Krankenzusatz, Risikoleben.

- [ ] Versicherungsschein
- [ ] Nachtrag zum Versicherungsschein
- [ ] Beitragsrechnung
- [ ] Beitragsanpassung
- [ ] Vertragsänderung
- [ ] Kündigung
- [ ] Leistungsfall
- [ ] Schadensmeldung
- [ ] Leistungsabrechnung

### Vorsorge

**Deutsche Rentenversicherung:** Renteninformation, Rentenauskunft,
Versicherungsverlauf, Kontenklärungsverfahren, Rentenbescheid.

**Zusatzversorgung:** Anmeldebestätigung, Änderungsmitteilungen, Stand des
Versorgungskontos, Renteninformation.

**Private Renten- und kapitalbildende Lebensversicherung:**
Versicherungsschein, Nachtrag, Anträge, Geschäftsbedingungen,
Jahresinformationen, Kosteninformationen, Rückkaufswerte, Kapitalwahlrecht.

**Bausparen:** Bausparvertrag, Jahreskontoauszüge, Zuteilungsmitteilungen,
Vertragsänderungen.

**Berufsunfähigkeit:** Versicherungsschein, Nachtrag,
Leistungsinformationen, Vertragsänderungen.

### Sonstiges

- [ ] Vereinsbeiträge
- [ ] Gewerkschaftsbeiträge
- [ ] Mitgliedsbescheinigungen
- [ ] Urkunden
- [ ] Allgemeine Bescheinigungen
- [ ] Schriftverkehr ohne feste Kategorie
- [ ] Informationsschreiben
- [ ] Sonstige Nachweise

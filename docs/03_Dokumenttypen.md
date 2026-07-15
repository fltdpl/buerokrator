# Dokumenttypen

## Gewählte Typen (implementiert)

- invoice
- tax (nur noch Finanzamt-Dokumente; Lohn/Gehalt siehe employment)
- insurance
- pension (inkl. Bausparen — kein eigener Typ)
- bank
- housing
- employment (Arbeit: Verträge, Kündigungen, Zeugnisse, Lohnsteuer/Gehalt, SV-Meldungen)
- legal (Recht: Anwalt/Gericht/Behörde; Korrespondenzpartner + Betreff)
- unknown (mit Freitext-Betreff)

Quelle: `src/core/document_types.py` bzw. `config/settings.yaml`.

**Konvention: Typ = Lebensbereich.** Eine Nebenkostenabrechnung ist
`housing`, nicht `invoice`; der Zahlungsaspekt ist das Feld `amount`.

## Kanonische Subtypen (`document_subtype`)

Zentral in `src/core/document_fields.py` (`KNOWN_SUBTYPES`), dort maßgeblich:

- **tax**: einkommensbescheinigung, bescheinigung
  (lohnsteuerbescheinigung/gehaltsabrechnung nach employment umgezogen)
- **employment**: arbeitsvertrag, kuendigung, arbeitszeugnis,
  lohnsteuerbescheinigung, gehaltsabrechnung, sv_meldung, sonstiges
- **pension**: contract, annual_statement, cost_statement,
  surrender_value_table, pension_information, bauspar_jahresauszug,
  steuerbescheinigung
- **housing**: nebenkostenabrechnung, mietvertrag, mieterhoehung,
  hausgeldabrechnung, sonstiges
- **bank**: kontoauszug, kreditkartenabrechnung, depotuebersicht, sonstiges

---

# Ideenspeicher: mögliche Dokumenttypen (nicht umgesetzt)

Brainstorming aus der Konzeptphase — kein Ist-Stand.

## Arbeit

### Dokumente
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

---

# Steuern

### Dokumente
- [ ] Lohnsteuerbescheinigung
- [ ] Einkommensteuerbescheid
- [ ] Kirchensteuerbescheid
- [ ] Solidaritätszuschlag
- [ ] Vorauszahlungsbescheide
- [ ] ELSTER-Unterlagen
- [ ] Steuerliche Bescheinigungen
- [ ] Spendenbescheinigungen
- [ ] Bescheinigungen für außergewöhnliche Belastungen

---

# Bank

### Dokumente
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

---

# Wohnen

### Dokumente
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

---

# Gesundheit

### Dokumente
- [ ] Arztrechnungen
- [ ] Zahnarztrechnungen
- [ ] Krankenhausrechnungen
- [ ] Rezepte
- [ ] Heil- [ ] und Kostenpläne
- [ ] Leistungsabrechnungen
- [ ] Bonusprogramme
- [ ] Gesundheitsbescheinigungen
- [ ] Impfbescheinigungen
- [ ] Pflegeunterlagen

---

# Versicherungen

### Versicherungsarten
- [ ] Haftpflichtversicherung
- [ ] Hausratversicherung
- [ ] Rechtsschutzversicherung
- [ ] Unfallversicherung
- [ ] Kfz-Versicherung
- [ ] Krankenzusatzversicherung
- [ ] Risikolebensversicherung

### Dokumente
- [ ] Versicherungsschein
- [ ] Nachtrag zum Versicherungsschein
- [ ] Beitragsrechnung
- [ ] Beitragsanpassung
- [ ] Vertragsänderung
- [ ] Kündigung
- [ ] Leistungsfall
- [ ] Schadensmeldung
- [ ] Leistungsabrechnung

---

# Vorsorge

### Deutsche Rentenversicherung (DRV)

#### Dokumente
- [ ] Renteninformation
- [ ] Rentenauskunft
- [ ] Versicherungsverlauf
- [ ] Kontenklärungsverfahren
- [ ] Rentenbescheid

### VBL / Zusatzversorgung

#### Dokumente
- [ ] Anmeldebestätigung
- [ ] Änderungsmitteilungen
- [ ] Stand des Versorgungskontos
- [ ] Renteninformation

### Private Rentenversicherung

#### Dokumente
- [ ] Versicherungsschein
- [ ] Nachtrag Versicherungsschein
- [ ] Anträge
- [ ] Geschäftsbedingungen
- [ ] Jahresinformationen
- [ ] Kosteninformationen
- [ ] Rückkaufswerte
- [ ] Kapitalwahlrecht

### Bausparen

#### Dokumente
- [ ] Bausparvertrag
- [ ] Jahreskontoauszüge
- [ ] Zuteilungsmitteilungen
- [ ] Vertragsänderungen

### Kapitalbildende Lebensversicherung

#### Dokumente
- [ ] Versicherungsschein
- [ ] Nachtrag Versicherungsschein
- [ ] Anträge
- [ ] Geschäftsbedingungen
- [ ] Jahresinformationen
- [ ] Rückkaufswerte

### Berufsunfähigkeitsversicherung

#### Dokumente
- [ ] Versicherungsschein
- [ ] Nachtrag Versicherungsschein
- [ ] Leistungsinformationen
- [ ] Vertragsänderungen

---

# Sonstiges

### Dokumente
- [ ] Vereinsbeiträge
- [ ] Gewerkschaftsbeiträge
- [ ] Mitgliedsbescheinigungen
- [ ] Urkunden
- [ ] Allgemeine Bescheinigungen
- [ ] Schriftverkehr ohne feste Kategorie
- [ ] Informationsschreiben
- [ ] Sonstige Nachweise
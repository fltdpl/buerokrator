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
- education (Ausbildung: Schul- und Hochschulzeugnisse, Urkunden,
  Fortbildungsnachweise; ohne Steuerrelevanz)
- health (Gesundheit: Arztunterlagen, Kassenbescheide, Reha, Atteste,
  Impfnachweise; ohne Steuerrelevanz)
- unknown (mit Freitext-Betreff)

**Konvention: Typ = Lebensbereich.** Eine Nebenkostenabrechnung ist
`housing`, nicht `invoice`; der Zahlungsaspekt ist das Feld `amount`.

### Abgrenzung employment ↔ education ↔ invoice

Entscheidend ist, **was bescheinigt wird**, nicht wer im Briefkopf steht
([ADR 014](decisions/014_kategorie_ausbildung.md)):

- Eine Arbeitsleistung im Arbeitsverhältnis → `employment`. Arbeits- und
  Zwischenzeugnisse bleiben dort.
- Eine Qualifikation oder Prüfungsleistung → `education`.
- Eine Schule oder Hochschule kann **Arbeitgeber** sein: Gehaltsabrechnung,
  Lohnsteuerbescheinigung und SV-Meldung einer Universität sind `employment`.
- Die Rechnung für einen Lehrgang ist `invoice`, die Teilnahmebescheinigung
  dazu `education` — wie bei Arztrechnungen, die `invoice` bleiben.

### Abgrenzung health ↔ invoice ↔ insurance ↔ employment

Derselbe Test, angewandt auf Gesundheit
([ADR 016](decisions/016_kategorie_gesundheit.md)):

- **Arztrechnungen bleiben `invoice`**, auch mit Diagnose darauf. Der Befund
  zur Behandlung ist `health`. Am Beleg hängt der Steuerzweck
  `krankheitskosten`.
- **Beiträge zur Kranken-/Pflegeversicherung bleiben `insurance`** — die
  Vorsorge-Auswertung erkennt sie an „kranken"/„pflege". Nur die
  Leistungsseite der Kasse (Kostenübernahme, Erstattung,
  Zuzahlungsbefreiung) ist `health`.
- Ein Krankenhaus kann **Arbeitgeber** sein: dessen Gehaltsabrechnung ist
  `employment`.
- Die **Arbeitsunfähigkeitsbescheinigung** ist `health` — bescheinigt wird
  ein Gesundheitszustand, nicht eine Arbeitsleistung.
- **Patientenverfügung und Vorsorgevollmacht** sind `legal`.

## Kanonische Subtypen (`document_subtype`)

Nur diese sieben Typen kennen Subtypen (`KNOWN_SUBTYPES`); bei den übrigen
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
- **education**: zeugnis, fortbildung, sonstiges
- **health**: arztunterlagen, krankenkasse, reha, attest, impfung, sonstiges

Frei eingegebene oder vom Modell erfundene Subtypen werden über
`SUBTYPE_ALIASES` und einen Fuzzy-Match auf dieses Vokabular normalisiert
(`normalize_subtype`).

Bei `education` trägt die **Alias-Tabelle die ganze Last**: der Fuzzy-Match
(Schwelle 0,85) erkennt keinen einzigen realen Wortlaut — „abschlusszeugnis"
liegt zu weit von „zeugnis" entfernt. Ohne Alias landet jedes echte Dokument
über `constrain_subtype` in `sonstiges`. Neue Wortlaute gehören deshalb dort
ergänzt, nicht dem Fuzzy-Match überlassen.

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

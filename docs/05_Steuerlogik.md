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

---

# Zielbild: ELSTER-Zuordnung (beschlossen 17.07.2026)

Die heutige Übersicht aggregiert nach Lebensbereichen — eine Steuererklärung
braucht aber Zahlen **pro ELSTER-Anlage**. Zielbild: die Steuer-Seite zeigt je
Anlage die übernahmefertigen Werte mit Beleg-Herleitung. Scope (typischer
Arbeitnehmer-Fall, erweitert 18.07.2026): **Anlage N (inkl. belegbasierter
Werbungskosten), Anlage Vorsorgeaufwand, Anlage KAP, Anlage Außergewöhnliche
Belastungen (Krankheitskosten)** — weitere Anlagen erst, wenn ein realer
Bestand sie braucht.

**Grenze des Systems (bewusst):** Die Erklärung enthält zwei Klassen von
Posten. **Belegbasierte** (Rechnungen: Steuerberatung, Arbeitsmittel,
Arzt-/Behandlungskosten …) kann ein Dokumentenarchiv liefern — dafür gibt es die
Zweck-Kennzeichnung `tax_purpose` (werbungskosten/krankheitskosten, DB-Spalte,
vom Nutzer beim Prüfen gesetzt, nie vom LLM; nur bei Rechnungen und nur,
wenn das Dokument steuerrelevant ist — andere Typen haben eigene
Steuerwege). **Angabenbasierte** (Entfernungspauschale aus Tagen × km,
Homeoffice-Tage, anteilige Telefonkosten, Verpflegungspauschalen) entstehen
aus Nutzerangaben, nicht aus Dokumenten — sie sind KOMPLETT außerhalb des
Projekt-Scopes (weder App noch Abgleich, Entscheidung 18.07.2026).

## Grundregeln

1. **In Anlagen-Summen fließen nur geprüfte UND steuerrelevante Dokumente.**
   Ungeprüfte Beträge erscheinen nie als Zahl, sondern als To-do
   („N Belege prüfen, bevor dieser Wert vollständig ist").
2. **Jede Summe ist herleitbar**: aufklappbar in „Beleg X 123 € + Beleg Y
   45 €" mit Links. Keine Blackbox-Zahlen.
3. Ampel je Anlagen-Position:
   - 🟢 übernahmefertig — alle zugehörigen Belege geprüft, keine Unklarheiten
   - 🟡 unvollständig — ungeprüfte Belege vorhanden
   - ❓ unklar — z. B. Versicherungsart fehlt
4. ELSTER-Zeilennummern ändern sich jährlich → wir verwenden stabile
   **Positions-Labels** (die Zeilen der Lohnsteuerbescheinigung sind dagegen
   stabil und werden referenziert).

## Zuordnung Anlage ← Dokumentfelder

### Anlage N (Einkünfte aus nichtselbständiger Arbeit)

Quelle: employment/lohnsteuerbescheinigung (nur steuerrelevante — die
Monats-Gehaltsabrechnungen sind redundant und zählen nicht).

| Position | LStB-Zeile | Feld | Status |
|---|---|---|---|
| Bruttoarbeitslohn | 3 | `gross_amount` | ✓ vorhanden |
| Einbehaltene Lohnsteuer | 4 | `income_tax` | ✓ vorhanden |
| Solidaritätszuschlag | 5 | `soli` | ✓ vorhanden |
| Kirchensteuer | 6/7 | `church_tax` | ✓ vorhanden |

**Werbungskosten aus Belegen** (Position `werbungskosten_belege`,
18.07.2026): Summe aller Dokumente mit `tax_purpose = werbungskosten`
(beliebiger Typ, Feld `amount`). Angabenbasierte Werbungskosten
(Entfernungspauschale, Homeoffice, Telefon-Anteil) bewusst NICHT — siehe
Grenze oben.

### Anlage Vorsorgeaufwand

| Position | Quelle | Feld | Status |
|---|---|---|---|
| Altersvorsorge: RV-Beitrag Arbeitnehmer | LStB Zeile 23 | `pension_insurance_employee` | ✓ ergänzt 17.07.2026 |
| Altersvorsorge: RV-Beitrag Arbeitgeber | LStB Zeile 22 | `pension_insurance_employer` | ✓ ergänzt 17.07.2026 |
| Basis-Krankenversicherung | LStB Zeile 25 | `health_insurance` | ✓ ergänzt 17.07.2026 |
| Pflegeversicherung | LStB Zeile 26 | `care_insurance` | ✓ ergänzt 17.07.2026 |
| Arbeitslosenversicherung | LStB Zeile 27 | `unemployment_insurance` | ✓ ergänzt 17.07.2026 |
| Private Kranken-/Pflege-Pflichtversicherung | LStB Zeile 28 | `private_health_insurance` | ✓ ergänzt 17.07.2026 |
| Sonstige Vorsorge (Haftpflicht, Unfall, BU, Risikoleben) | insurance-Dokumente | `amount` + `insurance_type`-Keywords | ✓ vorhanden (Logik: `document_deductibility`) |
| Zusatz-Krankenversicherung („über Basisabsicherung hinaus", eigene Anlagen-Zeile) | insurance-Dokumente mit „zusatz" (+ kranken/pflege/zahn) im Typ | eigene Position `insurance_health_supplementary` | ✓ ergänzt 18.07.2026 |

→ Feld-Lücke geschlossen (17.07.2026): die sechs SV-Felder (Z. 22–28) der Lohnsteuerbescheinigung. Ergänzen in
`document_fields.py` (lohnsteuerbescheinigung) + Prompt-Schema + form_schema
+ Kurzlabels (`document_display.py`).

### Anlage KAP (Kapitalerträge)

Quelle: NUR pension/steuerbescheinigung (aggregiert je Anbieter;
Bauspar-Jahresauszüge zählen nicht — Doppelzählung).

| Position | Feld | Status |
|---|---|---|
| Kapitalerträge/Zinsen | `interest` | ✓ vorhanden |
| Einbehaltene Kapitalertragsteuer | `capital_gains_tax` | ✓ vorhanden |
| Soli auf KESt | `soli` | ✓ vorhanden |
| Kirchensteuer auf KESt | `church_tax` | ✓ vorhanden |

### Anlage Außergewöhnliche Belastungen (18.07.2026)

Position `krankheitskosten_belege`: Summe aller Dokumente mit
`tax_purpose = krankheitskosten` (z. B. Arzt- oder Apothekenrechnungen).
Hinweis in
der Position: Erstattungen (Versicherung/Beihilfe) gegenrechnen — die
Erklärung verlangt beide Angaben.

## Erwartungsdatei (`tax_expected_<jahr>.yaml`, gitignored)

- Je Anlage ein Mapping `position: betrag`. Ganzzahlige Beträge gelten als
  gerundete Quelle (viele Steuerprogramme runden auf ganze Euro) → ±1 € Toleranz; Cent-Beträge cent-genau.
- `kap: nicht_abgegeben` — Anlage war nicht Teil der Erklärung; App-Werte
  dazu erscheinen als BEFUND (war die Erklärung unvollständig?), nicht als
  Abgleichsfehler.
- Tippfehler in Positions-Schlüsseln sind FEHLER (nie stilles „ok").
- Angabenbasierte Posten der Erklärung tauchen hier bewusst NICHT auf
  (out of scope, siehe Grenze oben).

## Vertrauens-Workflow (Entwicklungsprozess)

Ziel: der Nutzer kann sagen „diese Werte könnten so in die Erklärung".

1. **Unit-Tests im Repo** (erfundene Zahlen!): pro Anlagen-Position ein
   synthetischer Bestand mit handgerechneter Erwartung. Pflicht-Fälle:
   Doppelzählungs-Fallen (12 Gehaltsabrechnungen + LStB; Bauspar-Auszug +
   Steuerbescheinigung), ungeprüfte Belege (zählen nicht), zwei
   Teilzeit-LStB desselben Jahres (addieren sich).
2. **Golden-Master lokal (gitignored, echte Daten):** Nutzer pflegt
   `tax_expected_<jahr>.yaml` mit den Werten aus einer tatsächlich
   abgegebenen Erklärung (Ausdruck des Steuerprogramms oder Bescheid).
   Skript `tax_check.py <jahr>` vergleicht App-Ergebnis je Position und
   listet jede Differenz mit Beleg-Herleitung.
3. **Differenzen klassifizieren**, nicht wegoptimieren: (a) App-Fehler →
   fixen; (b) App fehlt ein Beleg → importieren; (c) **die damalige
   Erklärung war unvollständig** → Befund dokumentieren, App hat recht.
   Erst wenn jede Differenz erklärt ist, gilt das Jahr als abgenommen.
4. Das „im Aufbau"-Banner der Steuer-Seite fällt erst, wenn mindestens ein
   echtes Jahr abgenommen ist.

## Umsetzungsreihenfolge

1. ✅ Dieses Zielbild.
2. ✅ SV-Felder der Lohnsteuerbescheinigung (Z. 22–28) ergänzt (17.07.2026).
3. ✅ Service `src/tax/elster_mapping.py` (17.07.2026): Anlagen-Positionen
   (nur geprüft + steuerrelevant), Beleg-Herleitung, Ampel.
4. ✅ `tax_check.py` (18.07.2026): Golden-Master-Abgleich; Erwartungsdatei
   `tax_expected_<jahr>.yaml` gitignored (echte Steuerdaten). Vorlage:
   `python tax_check.py <jahr> --vorlage` (bewusst OHNE App-Werte
   vorbefüllt — Bestätigungsfehler vermeiden).
5. ✅ Steuer-Seite auf Anlagen-Ansicht umgebaut (18.07.2026): Ampel je
   Position, aufklappbare Beleg-Herleitung (gezählt/ungeprüft/ohne
   Wert/unklar), Lebensbereichs-Liste darunter erhalten.
6. Abgleich echtes Jahr, Differenzen klassifizieren, Abnahme.

## Ausbauideen (nicht umgesetzt)

Werbungskosten-Kennzeichnung an Rechnungen (s. o.), Spenden,
Handwerkerleistungen/§35a (Lohnanteil aus Nebenkostenabrechnungen),
Gesundheitskosten (dafür fehlen bisher passende Dokumenttypen, siehe
Ideenspeicher in [[03_Dokumenttypen]]).

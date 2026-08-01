# Steuerlogik

Implementiert in `src/tax/tax_summary.py`; GUI: Seite „Analyse", Tab
„Steuer" (Route `/analyse`; `/steuer` leitet um). Der zweite Tab
„Einkommen" zeigt die Jahreseinkommens-Auswertung
(`src/services/income_service.py`).

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

# ELSTER-Zuordnung

Die Lebensbereichs-Übersicht oben beantwortet nicht, was in die Erklärung
gehört — dafür braucht es Zahlen **pro ELSTER-Anlage**. Die Steuer-Seite
zeigt sie je Anlage übernahmefertig mit Beleg-Herleitung
(`src/tax/elster_mapping.py`). Scope ist der typische Arbeitnehmer-Fall:
**Anlage N (inkl. belegbasierter Werbungskosten), Anlage Vorsorgeaufwand,
Anlage KAP, Anlage Außergewöhnliche Belastungen (Krankheitskosten)** —
weitere Anlagen erst, wenn ein realer Bestand sie braucht.

**Grenze des Systems (bewusst):** Die Erklärung enthält zwei Klassen von
Posten. **Belegbasierte** (Rechnungen: Steuerberatung, Arbeitsmittel,
Arzt-/Behandlungskosten …) kann ein Dokumentenarchiv liefern — dafür gibt es die
Zweck-Kennzeichnung `tax_purpose` (werbungskosten/krankheitskosten, DB-Spalte,
vom Nutzer beim Prüfen gesetzt, nie vom LLM; nur bei Rechnungen und nur,
wenn das Dokument steuerrelevant ist — andere Typen haben eigene
Steuerwege). **Angabenbasierte** (Entfernungspauschale aus Tagen × km,
Homeoffice-Tage, anteilige Telefonkosten, Verpflegungspauschalen) entstehen
aus Nutzerangaben, nicht aus Dokumenten — sie sind KOMPLETT außerhalb des
Projekt-Scopes, weder in der App noch im Abgleich.

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

| Position | LStB-Zeile | Feld |
|---|---|---|
| Bruttoarbeitslohn | 3 | `gross_amount` |
| Einbehaltene Lohnsteuer | 4 | `income_tax` |
| Solidaritätszuschlag | 5 | `soli` |
| Kirchensteuer | 6/7 | `church_tax` |

Zusätzlich erfasst, aber bewusst OHNE eigene Anlagen-Position
(Werbungskosten-Kontext, siehe Grenze oben): LStB Zeile 17
(`commuting_allowance_taxfree`), Zeile 18 (`commuting_allowance_flat_taxed`),
Zeile 20 (`meal_allowance_taxfree`) — die Werte mindern bzw. betreffen
Entfernungspauschale und Verpflegungsmehraufwand und stehen für die
Erklärung am Dokument bereit.

**Werbungskosten aus Belegen** (Position `werbungskosten_belege`): Summe
aller Dokumente mit `tax_purpose = werbungskosten` (beliebiger Typ, Feld
`amount`). Angabenbasierte Werbungskosten (Entfernungspauschale,
Homeoffice, Telefon-Anteil) bewusst NICHT — siehe Grenze oben.

### Anlage Vorsorgeaufwand

| Position | Quelle | Feld |
|---|---|---|
| Altersvorsorge: RV-Beitrag Arbeitnehmer | LStB Zeile 23 | `pension_insurance_employee` |
| Altersvorsorge: RV-Beitrag Arbeitgeber | LStB Zeile 22 | `pension_insurance_employer` |
| Basis-Krankenversicherung | LStB Zeile 25 | `health_insurance` |
| Pflegeversicherung | LStB Zeile 26 | `care_insurance` |
| Arbeitslosenversicherung | LStB Zeile 27 | `unemployment_insurance` |
| Private Kranken-/Pflege-Pflichtversicherung | LStB Zeile 28 | `private_health_insurance` |
| Sonstige Vorsorge (Haftpflicht, Unfall, BU, Risikoleben) | insurance-Dokumente | `amount` + `insurance_type`-Keywords (Logik: `document_deductibility`) |
| Zusatz-Krankenversicherung („über Basisabsicherung hinaus", eigene Anlagen-Zeile) | insurance-Dokumente mit „zusatz" (+ kranken/pflege/zahn) im Typ | eigene Position `insurance_health_supplementary` |

### Anlage KAP (Kapitalerträge)

Quelle: NUR pension/steuerbescheinigung (aggregiert je Anbieter;
Bauspar-Jahresauszüge zählen nicht — Doppelzählung).

| Position | Feld |
|---|---|
| Kapitalerträge/Zinsen | `interest` |
| Einbehaltene Kapitalertragsteuer | `capital_gains_tax` |
| Soli auf KESt | `soli` |
| Kirchensteuer auf KESt | `church_tax` |

### Anlage Außergewöhnliche Belastungen

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
- `position: ignoriert` — die Differenz ist erklärt und bewusst
  ausgeklammert (z. B. App vollständiger als die damalige Erklärung,
  Bagatelle ohne Beleg). Bleibt im Report sichtbar (IGN), zählt aber
  nicht als Differenz; der Grund gehört als Kommentar daneben.
- Angabenbasierte Posten der Erklärung tauchen hier bewusst NICHT auf
  (out of scope, siehe Grenze oben).

Eine leere Vorlage legt `python -m tools.tax_check <jahr> --vorlage` an —
bewusst OHNE App-Werte vorbefüllt, sonst bestätigt man beim Ausfüllen nur
die eigenen Zahlen.

### § 35a Haushaltsnahe Dienstleistungen / Handwerker

Quelle: Wohnen-Abrechnungen (Nebenkosten-/Betriebskosten-, Heizkosten-,
Hausgeldabrechnung). Zwei Summenfelder je Dokument (LLM darf sie versuchen,
primär trägt sie der Nutzer beim Prüfen aus der § 35a-Bescheinigung nach):

| Position | Feld |
|---|---|
| Haushaltsnahe Dienstleistungen (§ 35a Abs. 2) | `household_services_amount` |
| Handwerkerleistungen (§ 35a Abs. 3, NUR Lohnanteil) | `craftsman_services_amount` |

Steuerrelevanz-Default für Wohnen: relevant, sobald ein § 35a-Feld gefüllt
ist. Abrechnungen ohne § 35a-Angaben erscheinen bewusst nicht als „fehlend"
(nicht jede Abrechnung weist solche Kosten aus). Die 20-%-Ermäßigung und
Höchstbeträge rechnet ELSTER — die App liefert Belegsummen.

**Jahreszuordnung (bewusst, kein tax_year-Feld):** § 35a-Kosten aus einer
Abrechnung setzt der Mieter im Jahr des ZUGANGS der Abrechnung an
(BMF-Schreiben zu § 35a) — das Dokumentdatum (Zustellung) ist also das
richtige Steuerjahr, genau wie die App über das Archivjahr zuordnet. Der
Abrechnungszeitraum („Betriebskosten 2024") gehört in den Betreff.

Die Abrechnungs-Subtypen speichern den Abrechnungsbetrag als
vorzeichenbehaftetes `settlement_amount` (Nachzahlung positiv, Guthaben
negativ — das generische `amount` ist Magnitude und konnte das nicht).

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
   `python -m tools.tax_check <jahr>` vergleicht App-Ergebnis je Position und
   listet jede Differenz mit Beleg-Herleitung.
3. **Differenzen klassifizieren**, nicht wegoptimieren: (a) App-Fehler →
   fixen; (b) App fehlt ein Beleg → importieren; (c) **die damalige
   Erklärung war unvollständig** → Befund dokumentieren, App hat recht
   (→ `ignoriert`-Vermerk in der Erwartungsdatei). Der Abgleich ist ein
   Hilfsmittel, um kritische Stellen zu finden — kein hartes Kriterium.
   Das Jahr gilt als abgenommen, wenn jede Differenz erklärt ist
   (Nutzer-Entscheidung, kein Exit-Code).
4. Das „im Aufbau"-Banner der Steuer-Seite fällt erst, wenn mindestens ein
   echtes Jahr abgenommen ist.

**Offen ist nur noch Schritt 3 für ein reales Jahr.**

## Ausbauideen (nicht umgesetzt)

Spenden (fehlt als Dokumenttyp/Subtyp); § 35a aus
Handwerker-EINZELrechnungen (bisher nur aus Wohnen-Abrechnungen —
Einzelrechnungen bräuchten einen eigenen tax_purpose-Wert); siehe
Ideenspeicher in [Dokumenttypen](03_Dokumenttypen.md).

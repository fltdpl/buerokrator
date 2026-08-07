# Entscheidung 014

## Thema

Eigener Dokumenttyp `education` („Ausbildung") — und wo genau seine Grenze
zu `employment` und `invoice` verläuft

## Entscheidung (07.08.2026)

Zeugnisse, Urkunden und Fortbildungsnachweise bekommen einen eigenen
Lebensbereich `education` mit drei Unterarten: `zeugnis`, `fortbildung`,
`sonstiges`. Der Typ hat **keine Steuerrelevanz** und **keine eigenen Felder** —
er nutzt `issuer`, `document_date` und `subject`.

Zwei Grenzen gelten dabei ausdrücklich:

1. **Arbeitszeugnisse bleiben `employment`.** Entscheidend ist, was
   bescheinigt wird: eine Arbeitsleistung im Arbeitsverhältnis gehört zum
   Lebensbereich Arbeit, eine Qualifikation oder Prüfungsleistung zur
   Ausbildung.
2. **Rechnungen bleiben `invoice`.** Die Rechnung für einen Lehrgang ist
   `invoice`, die Teilnahmebescheinigung dazu ist `education`.

## Begründung

**Der Lebensbereich fehlte, nicht die Steuerrelevanz.** Die Konvention des
Projekts ist „Typ = Lebensbereich"; Steuerrelevanz war nie das Kriterium
(`bank` und `legal` haben ebenfalls keine). Ohne eigenen Typ hat ein
Schulzeugnis nur zwei Auswege: `unknown` — oder, weil der Regel-Klassifikator
auf „zeugnis" anspringt, fälschlich `employment`.

**Genau das war bereits eingetreten.** Bei der Bestandsprüfung vor dem Bau
lagen mehrere echte Ausbildungsdokumente als `employment` mit der Unterart
`arbeitszeugnis` im Archiv — Masterurkunden und Hochschulzeugnisse, die das
Modell mangels passender Kategorie in die nächstgelegene gedrückt hatte.

**Der Typ ist billig.** Er kommt ohne neue Felder aus und braucht keine
Migration: die Feldsätze von `legal` und `arbeitszeugnis` sind bereits
`issuer`/`document_date`/`subject`, und die vorhandenen Arbeitszeugnisse
bleiben unberührt, wo sie sind.

**Die zweite Grenze folgt einem Präzedenzfall.** Arzt- und
Handwerkerrechnungen sind `invoice`, obwohl „Gesundheit" und „Wohnen" ebenso
Lebensbereiche wären. Der Zahlungsaspekt gehört auf die Rechnung, der
Nachweis in seinen Lebensbereich. So bleiben auch Fortbildungskosten dort, wo
die Steuerlogik sie erwartet.

## Folgen für den Regel-Klassifikator

Die Schlüsselwörter zielen ausschließlich auf **Dokumenttitel**, nie auf
Namen von Einrichtungen. „Hochschule" und „Universität" stehen bewusst nicht
in der Liste: Bildungseinrichtungen sind auch Arbeitgeber und stehen dann im
Briefkopf von Gehaltsabrechnungen und SV-Meldungen.

**„Abschlusszeugnis" ist nur ein schwaches Indiz (Gewicht 1).** Das Wort ist
arbeitsrechtlich ein stehender Begriff — Aufhebungsverträge sagen das
qualifizierte Abschlusszeugnis zu. Mit vollem Gewicht zog es am Bestand
gemessen Kündigungen nach `education`. Mit Gewicht 1 entscheidet es nie
allein und trägt nur bei, wenn ein zweites Indiz danebensteht; der Fall geht
sonst ans LLM, dessen Prompt die Abgrenzung kennt. Das ist die Linie aus
[008](008_rule_classifier_first.md): lieber keine Regel als eine falsche.

## Verworfen

- **Feinere Unterarten** (Schule / Hochschule / Berufsausbildung getrennt,
  dazu Förderung): mehr Unterarten heißt mehr Fehlklassifikation bei gleichem
  Feldsatz. Was genau bescheinigt wird, steht im Betreff.
- **Ein Feld für Note oder Abschluss:** jedes neue Feld kostet die volle
  Checkliste aus [009](009_field_whitelist.md), und der Wert wäre in keiner
  Auswertung verwendbar. Der Betreff trägt die Aussage.
- **Arbeitszeugnisse nach `education` umziehen:** hätte den Bestand migrieren
  müssen und widerspricht der Begründung, mit der seinerzeit die
  Lohnsteuerbescheinigung von `tax` nach `employment` wanderte (Aussteller ist
  der Arbeitgeber, der Lebensbereich ist Arbeit).

# Entscheidung 016

## Thema

Eigener Dokumenttyp `health` („Gesundheit") — und wo seine Grenzen zu
`invoice`, `insurance` und `employment` verlaufen

## Entscheidung (08.08.2026)

Arztunterlagen, Kassenbescheide und Nachweise bekommen einen eigenen
Lebensbereich `health` mit sechs Unterarten: `arztunterlagen`,
`krankenkasse`, `reha`, `attest`, `impfung`, `sonstiges`. Der Typ hat
**keine Steuerrelevanz** und **keine eigenen Felder** — er nutzt `issuer`,
`document_date` und `subject`, wie `education` und `legal`.

Drei Grenzen gelten ausdrücklich:

1. **Arztrechnungen bleiben `invoice`.** Auch mit Diagnose darauf. Der
   Befund zur Behandlung ist `health`, die Rechnung dazu `invoice`.
2. **Beiträge zur Kranken- und Pflegeversicherung bleiben `insurance`.**
   Nur die Leistungsseite der Kasse (Kostenübernahme, Erstattung,
   Zuzahlungsbefreiung, Krankengeld) ist `health`.
3. **Die Arbeitsunfähigkeitsbescheinigung ist `health`**, obwohl sie zur
   Vorlage beim Arbeitgeber bestimmt ist.

## Begründung

**Der Lebensbereich fehlte** — dieselbe Lage wie bei
[014](014_kategorie_ausbildung.md). Ein Arztbrief hatte bisher nur den Weg
nach `unknown`. Die Konvention „Typ = Lebensbereich" verlangt den Typ;
Steuerrelevanz war nie das Kriterium (`bank`, `legal` und `education` haben
ebenfalls keine).

**Grenze 1 folgt einem Präzedenzfall, den ADR 014 schon gezogen hat**: dort
stehen Arztrechnungen wörtlich als Beispiel dafür, dass der Zahlungsaspekt
auf die Rechnung gehört und der Nachweis in seinen Lebensbereich. Sie ist
zudem teuer, wenn sie bricht: am Beleg hängt der Steuerzweck
`krankheitskosten`, über den die Krankheitskosten in die Erklärung kommen.

**Grenze 2 ist die eigentlich gefährliche.** Die Vorsorge-Auswertung
erkennt absetzbare Beiträge an den Zeichenketten „kranken"/„pflege"
(`src/tax/tax_summary.py`, `src/tax/elster_mapping.py`). Zöge das Wort
„Krankenkasse" Dokumente nach `health`, fielen Vorsorgeaufwendungen **still**
aus der Steuererklärung — ohne Fehlermeldung, ohne sichtbare Spur. Deshalb
hat „krankenkasse" im Regel-Klassifikator nur Gewicht 1 und entscheidet nie
allein.

**Grenze 3 folgt dem Test aus ADR 014** („was wird bescheinigt?"): eine
Arbeitsunfähigkeit ist ein Gesundheitszustand, keine Arbeitsleistung. Dass
das Papier für den Arbeitgeber bestimmt ist, ändert den Absender nicht.

**Der Typ ist billig.** Keine neuen Felder, keine Migration,
`SCHEMA_VERSION` unverändert. Bestandsdokumente bleiben, wo sie sind.

## Folgen für den Regel-Klassifikator

Die Schlüsselwörter zielen ausschließlich auf **Dokumenttitel und
Textbausteine**, nie auf Einrichtungen. „Klinik", „Krankenhaus" und „Praxis"
stehen bewusst **nicht** in der Liste — Kliniken sind auch Arbeitgeber und
Rechnungssteller und zögen deren Gehaltsabrechnungen und Rechnungen hierher.
Das ist wörtlich die Lehre, mit der ADR 014 „Hochschule" ausgeschlossen hat.

Drei Wörter tragen nur Gewicht 1: **„krankenkasse"** (Grenze 2),
**„diagnose"** (steht auch auf Arztrechnungen) und **„attest"** (steckt in
„attestiert" und käme so in Rechtsschreiben vor).

## Am Bestand gemessen

Die Regel zieht **kein** vorhandenes Dokument nach `health`, und sie ändert
**keine** bestehende Entscheidung — der neue Typ nimmt keinem anderen den
Vorsprung. Die Nullmessung wurde gegen Positivfälle gegengeprüft, der Scan
ist nicht blind.

Aussagekräftiger als die Null: der Bestand **enthält** die Kollisionsfälle
beider Grenzen. Wo ein Dokument den Mindest-Score für `health` überhaupt
erreicht, liegt der gespeicherte Typ jeweils deutlich vorn — darunter
geprüfte Dokumente aus beiden Grenzbereichen. Beide Grenzen sind damit an
echten Dokumenten belegt und nicht nur an erfundenen Testtexten.

## Verworfen

- **Feinere Unterarten** (`rezept`, getrennte Fachrichtungen, `pflege` neben
  `krankenkasse`): mehr Unterarten heißt mehr Fehlklassifikation bei
  gleichem Feldsatz. Die Fachrichtung ist ohnehin der **Aussteller**, und
  worum es geht, steht im Betreff.
- **Ein Feld für Diagnose, Behandler oder Zeitraum:** jedes neue Feld kostet
  die volle Checkliste aus [009](009_field_whitelist.md), und der Wert wäre
  in keiner Auswertung verwendbar.
- **`amount` im Feldsatz:** die Kosten stehen auf der Rechnung. Sonst gäbe
  es zwei Orte für denselben Betrag.
- **Arztrechnungen nach `health` umziehen:** hätte den Bestand migrieren
  müssen und den Steuerzweck `krankheitskosten` mitgerissen.
- **Patientenverfügung und Vorsorgevollmacht nach `health`:** das sind
  Rechtsdokumente, die von Gesundheit handeln — sie bleiben `legal`.
- **Reduzierter Dateiname ohne Betreff** (erwogen, weil das Log Dateinamen
  führt und ein Betreff damit eine Diagnose im Klartext sein kann):
  verworfen als Nutzerentscheidung — ein Archiv voller
  „Datum_Praxis_Gesundheit.pdf" wäre unbrauchbar. Wer das nicht will, hält
  den Betreff allgemein.

## Datenschutz

Gesundheitsdaten sind besondere Kategorie personenbezogener Daten
(Art. 9 DSGVO). Für dieses Projekt folgt daraus nichts Neues an Mechanik,
aber eine Verschärfung der bestehenden Regel: in Code, Prompts, Aliassen,
Tests und Commit-Messages **keine** realen Praxen, Kassen, Diagnosen oder
Befundwortlaute. Die Alias-Tabelle enthält ausschließlich Gattungsbegriffe.

Dass die Extraktion lokal über Ollama läuft, ist genau hier der Gewinn des
Offline-Anspruchs ([002](002_ollama.md)): kein Befund verlässt den Rechner.

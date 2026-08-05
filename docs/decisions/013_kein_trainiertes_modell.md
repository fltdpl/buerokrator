# Entscheidung 013

## Thema

Kein eigenes trainiertes Modell — der geprüfte Bestand wird als Gedächtnis
und als Few-Shot-Quelle genutzt, nicht als Trainingsmenge

## Entscheidung (05.08.2026)

Die Klassifikation bleibt bei Regeln + lokalem LLM
([008](008_rule_classifier_first.md), [002](002_ollama.md)). Der wachsende
Bestand geprüfter Dokumente wird **nicht** zum Training eines eigenen
Klassifikators verwendet. Genutzt wird er zur Laufzeit an genau einer Stelle:
als Plausibilitäts-Hinweis beim Dokumenttyp im Prüf-Workflow
(`services/issuer_memory.type_mismatch`).

Zwei weitere Verwendungen wurden gebaut, am Bestand gemessen und wieder
entfernt — Few-Shot-Beispiele im Extraktions-Prompt und Feldvorschläge aus
konstanten Werten (siehe „Verworfen" unten). Beide Male war die Messung, nicht
die Plausibilität, der Ausschlag.

## Begründung

Anlass war die Frage, ob sich mit den inzwischen vorhandenen geprüften
Dokumenten ein klassischer Klassifikator oder ein neuronales Netz lohnt.
Gemessen wurde am eigenen Bestand statt geschätzt:

- **Die naheliegende Messung täuscht.** Ein Naive-Bayes-Klassifikator über
  TF-IDF wirkt bei zufälliger Aufteilung nahezu perfekt — aber das ist
  Leakage: die Dokumente verteilen sich auf wenige Aussteller, und
  Abrechnungen desselben Anbieters sind layoutgleich. Teilt man **nach
  Aussteller** (also so, wie ein neuer Anbieter tatsächlich ankommt), bricht
  die Genauigkeit deutlich ein und liegt klar unter dem LLM — auf den Fällen,
  die die Regeln nicht entscheiden, noch einmal deutlich darunter.
- **Die Klassenverteilung trägt kein überwachtes Lernen.** Mehrere der
  Dokumenttypen sind nur mit einer Handvoll Dokumenten belegt. Ein trainiertes
  Modell würde sie faktisch nie vorhersagen; das LLM kennt sie aus seinem
  Vortraining, ganz ohne Beispiel. Private Dokumentbestände sind extrem schief
  und langschwänzig — genau die Lage, in der Zero-Shot gewinnt.
- **Für die Felder fehlt das Labelformat.** Ein Sequence-Labeling-Modell
  bräuchte Positionen im Text; gespeichert ist nur Schlüssel → Wert. Nur rund
  zwei Drittel der geprüften Werte stehen überhaupt wörtlich im Dokumenttext
  — der Rest ist gerechnet, aus Spaltenlayouts zusammengesetzt oder
  normalisiert. Aus Rückwärtssuche gewonnene Labels erzeugten mehr Fehler als
  Signal.
- **Der Cold Start entscheidet.** Ein aus Nutzerdokumenten trainiertes Modell
  memoriert Nutzerdaten und dürfte weder ins Repository noch in ein Release.
  Jede Installation müsste selbst trainieren — beginnend bei null Dokumenten,
  also genau dann hilflos, wenn Hilfe am nötigsten wäre. Regeln + LLM
  funktionieren ab dem ersten Dokument.

## Verworfen: Feldvorschläge aus konstanten Werten

Ebenfalls gebaut und wieder entfernt: Vorschläge für leere Formularfelder,
deren Wert bei diesem Aussteller bisher unverändert war (Policennummer,
Produktname, Versicherungsart, Arbeitgeber).

Der Mechanismus funktionierte, war aber am Bestand **strukturell unsichtbar**.
Gemessen wurden zwei Größen, die nur zusammen etwas aussagen: wie oft ein
Vorschlag *berechnet* wird — und wie oft `form_fields(Typ, Subtyp)` das
betreffende Feld überhaupt *rendert*. Ergebnis: jeder einzelne berechnete
Vorschlag betraf `employer`, und zwar ausschließlich bei employment-Subtypen
(SV-Meldung, Arbeitsvertrag, Arbeitszeugnis, Sonstiges), deren Formular dieses
Feld bewusst nicht führt — dort ist `issuer` das gepflegte Feld. Sichtbar
wurden damit **null** Vorschläge.

Die Lehre ist allgemeiner: ein Vorschlag braucht die Schnittmenge aus „Feld im
Bestand konstant", „Feld hier leer" und „Feld im Formular vorhanden". Die
ersten beiden Bedingungen waren gemessen, die dritte nicht — und an ihr
scheiterte alles. **Ein Mechanismus-Test genügt nicht; es braucht die Messung,
wie oft das Feature am echten Bestand auslöst.**

Nicht nachgebessert wurde durch Verbreitern: `employer` in die
employment-Basisformulare aufzunehmen wäre eine Schema-Änderung mit eigener
Begründungslast, und der Vorschlag würde ein Feld füllen, das die Fachlogik
für diese Subtypen absichtlich leer lässt.

## Verworfen: Few-Shot im Extraktions-Prompt

Der naheliegende Weg, den Bestand ohne Training zu nutzen: dem Extraktor ein
früheres, geprüftes Dokument DESSELBEN Ausstellers samt seiner korrekten Werte
als Beispiel mitgeben. Es war gebaut, getestet und wurde an derselben
Qualitätsmessung geprüft, die auch die Baseline liefert — gleiche Dokumente,
gleiche Reihenfolge, einmal mit und einmal ohne Beispiel.

**Ergebnis: die Feldquote sank.** Und der vorab benannte Verdacht bestätigte
sich messbar — mehrere falsche Werte waren zeichengleich mit dem Beispiel: das
Modell schrieb ab, statt zu lesen. Der Schaden konzentrierte sich fast
vollständig auf `employment`; die kleineren Typen gewannen minimal, aber im
Rahmen des Rauschens (erkennbar daran, dass sogar die Klassifikation zwischen
beiden Läufen schwankte, obwohl das Beispiel sie gar nicht berührt).

Das ist plausibel: Gehaltsabrechnungen desselben Arbeitgebers sind layoutgleich
und unterscheiden sich nur in den Beträgen — ein Beispiel daraus ist maximal
verführerisch zum Abschreiben. Hinzu kommt, dass gerade dieser Typ mit dem
größten Textfenster arbeitet und das Beispiel das Kontextfenster des kleinen
Modells zusätzlich belastet.

Zwei Bedingungen, die dabei erarbeitet und gemessen wurden, sind
festgehalten, falls das Thema zurückkommt (die Auswahl des richtigen
Ausstellers funktionierte, das Beispiel selbst war das Problem):

- Der Aussteller muss **vor** der Extraktion aus dem Rohtext bestimmt werden,
  weil ihn erst die Extraktion liefert. Dabei gewinnt die **früheste**
  Fundstelle, nicht der längste Name: Dokumente nennen beiläufig fremde Firmen
  (Bankverbindung, Zahlungsempfänger, Vorversicherer), der Aussteller steht im
  Briefkopf.
- Der Fund zählt nur, wenn der Aussteller mit **mindestens drei** geprüften
  Dokumenten vertreten ist. Diese eine Bedingung senkt den Anteil falsch
  zugeordneter Beispiele um rund vier Fünftel, bei kaum geringerer Abdeckung.

Ein erneuter Versuch lohnt erst unter geänderten Voraussetzungen: ein größeres
Modell mit größerem Kontextfenster, oder ein Beispiel, dessen **Werte maskiert**
sind (es zeigt dann, wo etwas steht, ohne etwas zum Abschreiben anzubieten).
Ohne eine dieser Änderungen ist das Ergebnis reproduzierbar negativ.

## Konsequenzen

- Der Bestand wirkt über `issuer_memory` statt über Gewichte. Das ist
  erklärbar (jeder Hinweis lässt sich auf konkrete Vordokumente
  zurückführen), sofort wirksam und ohne Modellpflege.
- **Alles bleibt Hinweis.** Der Mehrheitstyp eines Ausstellers liegt am
  Bestand gemessen seltener richtig als die Klassifikation selbst und darf sie
  deshalb nicht überstimmen — dieselbe Haltung wie beim Dubletten-Hinweis.
- **Die Extraktion bleibt unverändert.** Der Bestand wirkt ausschließlich im
  Prüf-Workflow, wo ein Mensch jeden Hinweis sieht und wertet — nicht im
  Prompt, wo er unbemerkt Werte verfälschen kann.
- **Jede Nutzung des Bestands wird an ihm gemessen, bevor sie bleibt** — und
  zwar auf ihre Auslösequote, nicht nur auf ihre Mechanik. Von drei gebauten
  Verwendungen hat genau eine diese Prüfung bestanden.
- Keine neuen Abhängigkeiten: kein scikit-learn, kein torch, keine
  Embedding-Modelle. Der Offline- und Einfachheitsanspruch bleibt unberührt.
- **Wiedereinstieg**, falls die Frage zurückkommt: nicht Fine-Tuning, sondern
  ein zweiter Testdatensatz mit fremden Anbietern (siehe `todo.md`). Er würde
  die Messung härten, an der diese Entscheidung hängt — die Richtung ändert er
  nach heutigem Stand nicht.

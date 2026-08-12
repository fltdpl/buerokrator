# Buerokrator

## Changelog

## Unveröffentlicht

- **Behoben: Nach einer Wiederherstellung blieb das PDF „nicht gefunden“.**
  Jedes Dokument merkt sich, wo seine Datei liegt. Wurde eine Sicherung an
  einem **anderen Ort** eingespielt — etwa in eine frisch installierte App —,
  lagen die Dokumente danach zwar richtig im Archiv, aber die gemerkten
  Orte zeigten noch dorthin, wo der Bestand zur Sicherungszeit lag. Die
  Folge war still: in der Detailansicht stimmten alle Werte, nur das PDF
  fehlte mit der Meldung „PDF-Datei nicht gefunden“. Neu importierte
  Dokumente waren nie betroffen — deshalb fiel es erst spät auf.

  **Die Wiederherstellung bindet die Dateien jetzt selbst neu an**, und für
  Bestände, die den Fehler schon haben, gibt es
  **Einstellungen → Datenbank → Archivpfade**: dort steht, wie viele
  Dokumente ihre Datei nicht finden, und ein Knopf bindet sie neu. Vorher
  entsteht eine Sicherung der Datenbank; geändert wird nur, wo die Datei
  wirklich gefunden wurde — **geraten wird nie**. Aus dem Quellcode geht
  dasselbe mit `python -m tools.repair_archive_paths`.

- **Behoben: ältere Dokumente mit unvollständig gespeichertem Ort.** Aus
  früheren Programmversionen stammen Einträge, deren Ort nur relativ
  vermerkt ist. Sie wurden je nach Startart der App gefunden oder eben
  nicht. Jetzt werden sie immer gegen den Bestand der aktiven Person
  aufgelöst — das betrifft Anzeige, Download, Dateigröße und Papierkorb.

- Die Meldung „PDF-Datei nicht gefunden“ nennt jetzt den nächsten Schritt.

## v0.3.0 — 09.08.2026

- **Neu: Bestand aus einer älteren Version zieht auf Knopfdruck um.** Seit
  der Einführung mehrerer Personen liegen die Unterlagen in einem eigenen
  Ordner je Person. Wer von Version 0.2.x kommt, hat sie noch eine Ebene
  höher liegen — die App hätte sie dort nicht gefunden und ein leeres
  Archiv gezeigt, obwohl nichts verloren war.

  Beim Start meldet sie das jetzt und bietet den Umzug an: **Datenbank und
  Archiv werden kopiert**, danach prüft die App, ob jedes Dokument am neuen
  Ort wirklich liegt, und erst dann schaltet sie um. **Die Originale bleiben
  als Sicherung liegen — gelöscht wird nichts**, und schlägt etwas fehl,
  bleibt alles, wie es war. Wer die App aus dem Quellcode betreibt, kann
  denselben Umzug weiterhin mit `python -m tools.port_to_profiles` auslösen.

  Während ein Stapel-Import läuft, ist der Umzug gesperrt — sonst schriebe
  der Rest des Stapels in einen Bestand, der gerade wegzieht.

- **Ruhigere Seitenleiste.** Der Umschalter für die Person steht jetzt klein
  **neben** dem Namen statt als eigene Zeile darunter — dort las er sich wie
  ein weiterer Menüpunkt. Über **Beenden** liegt eine Trennlinie: es verlässt
  das Programm, statt darin zu navigieren, und soll nicht wie der nächste
  Menüpunkt aussehen.
- **Der Hinweis „Die Steuer-Funktion ist noch im Aufbau“ ist weg.** Die
  Summen und die Einordnung haben sich an einem echten Jahrgang bewährt.
  Sie bleiben eine Vorbereitung der Erklärung, keine Steuerberatung — das
  sagt die Anleitung, dafür braucht es kein Banner auf jeder Ansicht.

- **Neu: Tags an Dokumenten (erster Schritt).** Beim Prüfen lässt sich
  jedem Dokument eine beliebige Zahl von Stichwörtern anhängen — für **alle**
  Kategorien. Damit lässt sich zusammenhalten, was quer durch die Kategorien
  gehört: der Befund, die Rechnung und die Krankmeldung zu **derselben**
  Behandlung.

  Ein Tag ist einfach ein Wort — „Knie-OP“, „Auto“, „Umzug 2026“. Keine
  Systematik, keine Pflicht: Dokumente ohne Tags bleiben, wie sie sind, und
  wo keine vergeben sind, steht nur ein kleiner Knopf **＋ Tag**. Jedes Tag
  bekommt automatisch einen farbigen Punkt, damit man es in einer Reihe
  wiedererkennt.

  Der Knopf öffnet eine Liste aller bisherigen Tags zum Ankreuzen, mit
  Suchfeld — Wiederverwenden ist der häufigere Fall als Neuanlegen. Ein neues
  Tag entsteht über **Neues Tag anlegen** und wird erst beim **Speichern**
  wirklich angelegt; wer die Seite verlässt, ohne zu speichern, hinterlässt
  nichts.

  Groß- und Kleinschreibung wird beim Vergleich ignoriert, damit „Knie“ und
  „knie“ nicht als zwei Stichwörter nebeneinander stehen — die Schreibweise,
  mit der Sie ein Tag angelegt haben, bleibt aber erhalten.

  Die Datenbank wird dafür einmalig erweitert; vorher legt die App
  automatisch eine Sicherung neben der Datenbank an.
- **Neu: Tags an viele Dokumente auf einmal — und danach filtern.** In der
  Dokumentenliste lässt sich eine Auswahl markieren und ihr mit
  **＋ Vergeben** ein Stichwort anhängen oder es mit **− Entfernen** wieder
  abnehmen. Vorhandene Tags der Dokumente bleiben dabei erhalten; ein noch
  unbekanntes Tag entsteht mit dem Knopf. Erst damit lässt sich ein
  gewachsener Bestand überhaupt erschließen — Dokument für Dokument wäre
  das nicht zu schaffen.

  Dazu ein **Tag-Feld in der Filterleiste**. Es erscheint nur, wenn es Tags
  gibt, und bleibt anders als der Unterart-Filter auch bei „Kategorie: Alle“
  stehen — quer über die Kategorien zu suchen ist der Zweck von Tags.
  Mehrere ausgewählte Tags gelten **zusammen**: angezeigt wird, was alle
  davon trägt.

- **Neu: Tags in der Trefferliste — und in der Suche.** Die Dokumentenliste
  zeigt die Tags jetzt klein unter dem Dokumentnamen, mit ihrem farbigen
  Punkt. Keine neue Spalte: die Liste ist ohnehin breit genug.

  **Ein Klick auf ein Tag filtert danach.** Ein zweiter Klick auf ein
  anderes engt weiter ein — angezeigt wird, was beide trägt. Die Zeile
  darunter öffnet sich dabei nicht.

  Außerdem findet das **Volltextfeld** die Tags jetzt mit: „knie“ eintippen
  genügt, es braucht keine besondere Schreibweise. Treffer im Tag stehen
  dabei **vor** bloßen Textfundstellen — ein Tag ist die einzige Angabe, die
  Sie bewusst über ein Dokument vergeben haben.

  Bereits vergebene Tags werden dabei einmalig nachgetragen; die Datenbank
  wird erneut erweitert und vorher wieder gesichert.

- **Neu: Tags verwalten.** *Einstellungen → Tags* zeigt alle vergebenen
  Stichwörter mit der Zahl der Dokumente, an denen sie hängen.

  **Umbenennen** geht direkt im Namensfeld — auch nur die Schreibweise
  („knie-op" → „Knie-OP"). **Zusammenführen** räumt auf, was die App nicht
  erraten kann: Groß- und Kleinschreibung fängt sie ab, aber „Knie OP" und
  „Knie-OP" sind für sie zwei Dinge. Beim Zusammenführen ziehen alle
  Dokumente des einen Tags auf das andere um, ohne doppelte Einträge.

  Dazu die **Farbe** — sechs Punkte zur Auswahl, die aktuelle ist
  hervorgehoben — und **Löschen** mit Rückfrage, die vorher sagt, von wie
  vielen Dokumenten das Stichwort verschwindet. Die Dokumente selbst bleiben
  dabei unangetastet.

  Alle vier Änderungen wirken sofort auch in der Suche: nach einem
  Umbenennen findet man das Tag unter dem neuen Namen, nicht mehr unter dem
  alten.
- **Neu: Kategorie „Gesundheit".** Arztbriefe, Befunde, Bescheide der
  Krankenkasse, Reha-Unterlagen, Atteste und Impfnachweise haben jetzt einen
  eigenen Lebensbereich mit den Unterarten **Arztunterlagen / Befund**,
  **Krankenkasse**, **Reha / Kur**, **Attest / AU**, **Impfung** und
  **Sonstiges**. Sie bekommen einen eigenen Archivordner und lassen sich
  filtern, statt unter „Sonstiges" zu landen.

  Zwei Abgrenzungen sind bewusst so gewählt:

  **Arztrechnungen bleiben „Rechnung"** — auch wenn eine Diagnose darauf
  steht. Der Befund zur Behandlung gehört zu Gesundheit, die Rechnung dazu
  bleibt bei den Rechnungen, weil dort die Krankheitskosten für die
  Steuererklärung hängen.

  **Bescheinigungen über Kranken- und Pflegeversicherungs-Beiträge bleiben
  „Versicherung"** — sie sind Vorsorgeaufwendungen und werden als solche
  ausgewertet. Nur die Leistungsseite der Kasse (Kostenübernahme,
  Erstattung, Zuzahlungsbefreiung) ist Gesundheit.

  Die Arbeitsunfähigkeitsbescheinigung zählt zu Gesundheit, auch wenn sie
  beim Arbeitgeber vorzulegen ist. Patientenverfügung und Vorsorgevollmacht
  bleiben bei „Recht".

  Am vorhandenen Bestand wurde nichts umsortiert und keine bestehende
  Zuordnung verändert; Bestandsdokumente wandern nur, wenn Sie sie selbst
  umstellen ([ADR 016](docs/decisions/016_kategorie_gesundheit.md)).
- **Neu: Deinstallation mit einem Befehl.** Bisher verteilte die
  Installation das Programm auf vier Verzeichnisse, und wer es wieder
  loswerden wollte, musste sie einzeln von Hand aufräumen. Jetzt liegt ein
  Deinstaller neben dem Programm:

  ```bash
  ~/.local/opt/buerokrator/uninstall.sh
  ```

  Er zeigt erst, was er entfernen wird, und fragt nach. Der Menüeintrag
  verschwindet dabei sofort und bleibt nicht als Karteileiche stehen.

  **Ihre Dokumente, die Datenbank und die Einstellungen rührt er nicht an** —
  eine erneute Installation findet sie an derselben Stelle wieder. Wer sie
  mit wegräumen möchte, ruft `uninstall.sh --daten-verschieben` auf: der
  Datenordner wandert dann nach `~/buerokrator-daten-<datum>`. **Gelöscht
  wird er auch dann nicht**, das bleibt eine bewusste Handbewegung.

  Ein Starter gleichen Namens in `~/.local/bin`, der nicht zu dieser
  Installation gehört, bleibt ebenfalls stehen.
- **Neu: mehrere Personen an einer Installation.** Wer den Haushalt teilt,
  kann in den Einstellungen unter „Profile" eine zweite Person aufnehmen.
  Jede bekommt einen **eigenen, vollständig getrennten Bestand**: eigene
  Dokumente, eigenes Archiv, eigene Aussteller-Aliase — und damit auch
  getrennte Steuersummen, denn zwei Menschen geben getrennte Erklärungen ab.
  Die Einstellungen (Tesseract, Modell, Kategorien) gelten weiter für alle.

  Der bisherige Bestand zieht dabei in einen eigenen Ordner um. **Gelöscht
  wird nichts** — die Originale bleiben als Sicherung liegen, und auch das
  Entfernen einer Person nimmt sie nur aus der Liste.

  Das **Nutzerprofil steht immer in der Seitenleiste**, direkt unter dem
  Programmnamen — auch wenn nur eine Person eingerichtet ist. Sobald es eine
  zweite gibt, erscheint darunter „Benutzer wechseln"; wer geöffnet ist,
  zeigen zusätzlich Dashboard und Import-Seite. **Während ein Import läuft,
  ist der Wechsel gesperrt** — sonst landete der Rest des Stapels im falschen
  Bestand.

  Mehr als fünf Personen sind nicht vorgesehen. Eine Person zu entfernen nimmt
  sie nur aus der Liste; ihr Ordner bleibt liegen.

  **Für bestehende Installationen:** die Dokumente liegen künftig unter
  `profiles/<kennung>/`. Ein gewachsener Bestand zieht einmalig mit
  `python -m tools.port_to_profiles` um — kopierend, mit Gegenprobe, und die
  Originale bleiben als Sicherung liegen
  ([ADR 015](docs/decisions/015_mehrbenutzer_profile.md)).
- **Neu: Kategorie „Ausbildung".** Schul- und Hochschulzeugnisse, Urkunden
  und Fortbildungsnachweise haben jetzt einen eigenen Lebensbereich mit den
  Unterarten **Zeugnis / Urkunde**, **Fortbildung / Zertifikat** und
  **Sonstiges**. Sie bekommen einen eigenen Archivordner und lassen sich
  filtern, statt unter „Sonstiges" oder fälschlich unter „Arbeit" zu landen.

  **Arbeitszeugnisse bleiben bei „Arbeit"** — dort wird eine Arbeitsleistung
  bescheinigt, hier eine Qualifikation. Und die Rechnung für einen Lehrgang
  bleibt eine Rechnung; nur der Nachweis dazu ist Ausbildung.

  **Bestandsdokumente ziehen nicht von selbst nach.** Wer Zeugnisse schon
  importiert hat, findet sie womöglich unter „Arbeit" — sie wandern über
  „Erneut prüfen" oder durch Umstellen des Typs im Prüf-Workflow. Die
  Ausbildungskategorie ist bewusst **nicht steuerrelevant**.
- **Neu: Hinweis, wenn ein Dokument nicht zum Aussteller passt.** Die meisten
  Dokumente kommen von einem Anbieter, der längst im Archiv liegt. Hat dieser
  bisher **ausnahmslos** einen anderen Dokumenttyp geschickt, sagt der
  Prüf-Workflow das jetzt — genau die Konstellation, in der eine
  Fehlklassifikation sonst unbemerkt durchginge.

  Ein **Hinweis, keine Automatik**: der erkannte Typ wird nicht überschrieben,
  die Wertung bleibt beim Nutzer. Bewusst eng gefasst, damit er nicht zum
  Rauschen wird — Anbieter, die legitim mehrere Sparten liefern (Vorsorge und
  Versicherung aus einem Haus), lösen ihn nie aus. Wer keine Vorgeschichte
  hat, merkt nichts davon.
- **Neu: die Suche zeigt die Fundstelle.** Bisher stand in der Trefferliste
  nur, WELCHE Dokumente passen — nicht, an welcher Stelle. Steht der
  Suchbegriff im Dokumenttext, zeigt eine Spalte „Fundstelle" jetzt die
  Passage mit hervorgehobenem Begriff. Sie erscheint nur, wenn es wirklich
  einen Treffer im Text gibt: Treffer in Dateiname, Feldern oder Notiz sind
  in der Zeile ohnehin schon zu sehen.
- **Neu: Hinweis auf inhaltliche Dubletten.** Derselbe Beleg ein zweites Mal
  eingescannt hat andere Bytes und rutschte an der Dubletten-Prüfung des
  Imports vorbei. Der Prüf-Workflow vergleicht jetzt zusätzlich die
  erkannten Werte (gleicher Aussteller plus gleiche Rechnungsnummer oder
  gleicher Betrag und gleiches Datum) und verlinkt das mögliche Gegenstück
  — ohne automatisch zu löschen. Der Hinweis nennt dabei nicht nur, was
  übereinstimmt, sondern auch, welche Felder **widersprechen** (etwa eine
  abweichende Rechnungsnummer) — daran entscheidet sich am Original, ob es
  wirklich derselbe Beleg ist. Angezeigt wird der Widerspruch, gefiltert
  wird nicht: er kann auch ein Lesefehler in einem der beiden Scans sein.
- **Behoben: „Speichern" gab das Dokument still frei.** Beide Knöpfe führten
  zum Status „geprüft" — der Unterschied war nur, ob danach zum nächsten
  Dokument gesprungen wird. Ein zwischendurch gespeichertes Dokument zählte
  damit sofort in die geprüften Steuersummen und in die Qualitätsmessung, ohne
  dass jemand es freigegeben hatte. „💾 Speichern" lässt den Status jetzt, wie
  er ist; freigegeben wird nur über „✅ Speichern & Freigeben". Bestehende
  Freigaben bleiben unverändert — wer sie zurücknehmen möchte, nutzt in der
  Dokumentenliste „Freigabe widerrufen".
- **Behoben: der Import erfand Unterarten.** Passte ein Bank-Dokument in
  keine der bekannten Unterarten, schrieb die Erkennung stattdessen die
  Betreffzeile in das Feld „Unterart" — im Filter standen dadurch Unterarten,
  die es gar nicht gibt. Erkannte Unterarten sind jetzt auf das Vokabular des
  jeweiligen Dokumenttyps festgelegt; passt keine, steht „Sonstiges", und der
  Wortlaut wandert in den Betreff, wo er hingehört. Bestehende Dokumente
  bekommen das über „Erneut prüfen" oder eine einmalige Auswahl im
  Prüf-Workflow.
- **Behoben: Bank-Dokumente trugen das Datum im falschen Format** —
  „2019-05-23" statt „23.05.2019", also anders als alle übrigen Dokumente.
  Datumsfelder werden jetzt einheitlich deutsch geführt, unabhängig davon,
  was die Erkennung liefert; bestehende Dokumente ziehen beim nächsten
  Speichern nach. An der Sortierung im Archiv ändert sich nichts — Dateinamen
  beginnen weiterhin mit Jahr-Monat-Tag.
- **Behoben: das Anwendungs-Log war nach einer Rotation für andere Benutzer
  des Rechners lesbar.** Es enthält Dateinamen und ist deshalb auf den
  Besitzer beschränkt; die bei der Rotation neu angelegte Datei erbte diese
  Beschränkung bisher nicht.
- **Behoben: nicht klassifizierte Dokumente hießen alle `unknown.pdf`** —
  ohne Datum und ohne Aussteller, sodass mehrere davon nur noch über einen
  angehängten Zähler zu unterscheiden waren. Sie bekommen jetzt denselben
  Namensaufbau wie die übrigen Typen (Datum, Aussteller, Betreff).
  Bestehende Dateien werden beim nächsten Speichern umbenannt.
- **Behoben: Datumsangaben mit zweistelligem Jahr oder ausgeschriebenem
  Monat** („05.03.19", „7. Juni 2016") landeten roh im Dateinamen; sie
  werden jetzt normalisiert. Bestehende Dateien werden beim nächsten
  Speichern umbenannt.
- **Behoben: Backup war unter WAL nicht konsistent** — frisch gespeicherte
  Dokumente konnten in der Sicherung fehlen, wenn parallel ein Import lief.
  Die Datenbank wird jetzt über die SQLite-Backup-API gelesen.
- **Behoben: Beträge im englischen Zahlenformat** („1,234.56") wurden um
  den Faktor 1000 falsch verrechnet.
- **Behoben: Sonderzeichen in erkannten Datumsangaben** konnten beim
  Archivieren aus dem Archivordner herausführen; der Dateiname wird jetzt
  zentral abgesichert (inkl. der unter Windows verbotenen Zeichen).
- **Behoben: Import meldet jetzt die Ursache** eines fehlgeschlagenen
  Dokuments statt nur den Dateinamen.
- Datenbank-Migration ist gegen gleichzeitige Zugriffe abgesichert.
- Testläufe schreiben nicht mehr in das Log einer vorhandenen Installation;
  ihre Fehlerzeilen waren dort von echten nicht zu unterscheiden.
- Neue Doku-Seite `docs/09_Pruefworkflow.md`: Zustände eines Dokuments,
  Ablauf der Prüfseite und was beim Speichern passiert — als Diagramme.
- **Entfernt: der alte Live-Ordner-Watcher.** Er überwachte den
  `inbox`-Ordner und verarbeitete Dateien sofort, kannte aber keine
  Dubletten-Erkennung und war seit dem Stapel-Import über die Import-Seite
  ohne Zweck. Damit entfällt auch die Abhängigkeit `watchdog`.
  `python main.py` startet jetzt einfach die App.
- Die CLI-Werkzeuge liegen in `tools/`: `python -m tools.evaluate` und
  `python -m tools.tax_check <jahr>` statt der bisherigen Skripte im
  Wurzelverzeichnis.

## v0.2.1 — 25.07.2026

- Behoben: Ein zweiter Start (z. B. Klick im Anwendungsmenü, während die
  App im Hintergrund läuft) scheiterte stumm am belegten Port — jetzt
  öffnet er den Browser zur bereits laufenden Instanz; ist der Port durch
  ein fremdes Programm belegt, steht eine klare Meldung im `console.log`.
- Behoben: Im Anwendungsmenü erschien statt des Logos ein generisches
  Symbol — der Menüeintrag verweist jetzt auf einen absoluten Icon-Pfad
  im Installationsverzeichnis.

## v0.2.0 — 25.07.2026

### Steuervorbereitung: ELSTER-Anlagen-Ansicht

- Die Steuer-Ansicht zeigt je ELSTER-Anlage (N, Vorsorgeaufwand, KAP,
  außergewöhnliche Belastungen, § 35a) übernahmefertige Werte mit Ampel und
  aufklappbarer Beleg-Herleitung — in Summen fließen nur geprüfte,
  steuerrelevante Dokumente.
- Zweck-Kennzeichnung für Rechnungen (Werbungskosten/Krankheitskosten),
  § 35a-Belegsummen aus Wohnen-Abrechnungen, Zusatz-Krankenversicherung als
  eigene Position.
- Lohnsteuerbescheinigung vollständiger: Sozialversicherungs-Zeilen 22–28
  und Arbeitgeber-Leistungen (Zeilen 17/18/20) in Schema, Formular und
  Extraktion.
- Neu: `tax_check.py` — Abgleich der App-Werte gegen die tatsächlich
  abgegebene Erklärung (lokale Erwartungsdatei); als Hinweis-Werkzeug mit
  erklärbaren Differenzen (`ignoriert`-Vermerk).

### Neue Analyse-Seite

- „Steuer" und „Einkommen" als Tabs unter einer Seite; die
  Einkommens-Auswertung zeigt Brutto, Steuern und rechnerisches Netto über
  die Jahre aus den geprüften Lohnsteuerbescheinigungen — als Diagramm mit
  Beleg-Herleitung je Jahr.

### Bessere Dokumentenerkennung

- PDF-Textextraktion layouttreu (Zeichenpositionen statt Druckreihenfolge)
  — Grundlage für deterministische Regelparser: Lohnsteuerbescheinigung,
  SV-Meldung und Entgeltnachweis werden jetzt regelbasiert gelesen, das LLM
  liefert nur noch die Restfelder.
- Wohnen: Abrechnungs-Subtypen mit vorzeichenbehaftetem Abrechnungsbetrag
  (Guthaben negativ), neuer Subtyp Heizkostenabrechnung.

### Suche & Verwaltung

- Volltextsuche auf SQLite FTS5 mit Relevanz-Ranking (auch Teilbegriffe).
- Dokumentenliste: Bulk-Aktionen „Aussteller vereinheitlichen" und
  „Freigabe widerrufen", Unterart-Filter.
- Aussteller-Aliase: Schreibweisen desselben Ausstellers werden schon beim
  Import vereinheitlicht — pflegbar direkt in der App (Einstellungen →
  Aliase) oder als Textdatei.

### Sonstiges

- Neues Logo; Backup-Wiederherstellung in den Einstellungen;
  Datenbank-Migrationen laufen automatisch mit Backup vor jeder
  Schemaänderung (v1 → v3).

## v0.1.0 — 16.07.2026

Erstes Release: Import-Pipeline (OCR, Klassifikation, Extraktion,
Archivierung), Prüf-Workflow, Dokumentenliste, Steuerübersicht,
Papierkorb, Backup, First-Run-Assistent, Linux-Paket (Tarball +
install.sh).

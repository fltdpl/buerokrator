# Buerokrator

## Changelog

## Unveröffentlicht

- Intern: Grundlage für mehrere Personen an einer Installation — die App
  unterscheidet jetzt zwischen dem Verzeichnis der Installation
  (Einstellungen, Log) und dem des Datenbestands. Ohne angelegte Profile
  ändert sich nichts ([ADR 015](docs/decisions/015_mehrbenutzer_profile.md)).
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

# Buerokrator

## Changelog

## Unveröffentlicht

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

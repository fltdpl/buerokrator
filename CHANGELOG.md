# Changelog

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

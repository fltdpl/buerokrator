# Projekt-Roadmap

## Abgeschlossene Grundphasen (Juni/Juli 2026)

Logging, Verarbeitungs-Pipeline mit Fehlerbehandlung,
OCR (vorhandener PDF-Text bevorzugt, Tesseract für Scans), Ollama-Anbindung
mit Klassifikations-Prompt und JSON-Ausgabe, Dateinamensschema und
Archivierung, SQLite mit Jahresübersicht und CSV-Export.

Offen aus diesen Phasen: Excel-Export, chancenorientierte
Rentenversicherung erfassen.

Der ursprüngliche Live-Ordner-Watcher wurde am 01.08.2026 entfernt — der
Stapel-Import über die Import-Seite hatte ihn längst abgelöst, und mit ihm
fielen ein ungetestetes Modul und die Abhängigkeit `watchdog` weg.

## Dokumentenerkennung

### Hoch

- [x] Volltextsuche über OCR-Inhalte (`document_text`)
    
- [x] Suchergebnisse nach Relevanz sortieren (bm25 über FTS5) ✅ 2026-07-17
    
- [x] OCR-Text dauerhaft für alle Importwege speichern (`document_text` bei jedem Insert) ✅ 2026-07-15
    
- [ ] OCR-Qualität bei Scans verbessern
    
- [ ] Erkennung von mehrseitigen Dokumenten testen
    
- [ ] Fehlerhafte OCR-Ergebnisse protokollieren
    

### Dokumentklassifikation

- [x] Klassifikationsgenauigkeit messen (`evaluate.py`, je Typ und Quelle rule/llm) ✅ 2026-07-08
    
- [x] Testdatensatz mit echten Dokumenten aufbauen (geprüfte Dokumente in der DB als Ground Truth) ✅ 2026-07-08
    
- [ ] Klassifikation "unknown" analysieren
    
- [x] Regelbasierte Erkennung vor LLM-Klassifikation prüfen ✅ 2026-07-01
    
- [ ] Konfidenzscore für Dokumenttyp speichern
    

### Datenextraktion

- [ ] Fehlende Felder erkennen und markieren
    
- [x] Extraktionsqualität messen (`evaluate.py` gegen geprüfte Dokumente als Ground Truth; Baseline 15.07.2026 aufgenommen und am 25.07.2026 nach den Juli-Umbauten bestätigt — Messwerte lokal in `HANDOVER.md`) ✅ 2026-07-08
    
- [ ] Validierung von Datumsangaben
    
- [ ] Validierung von Beträgen
    
- [ ] Validierung von Vertragsnummern
    
- [ ] Validierung von Versicherungsnummern
    

### Neue Dokumenttypen

- [x] Kontoauszüge (bank-Subtyp) ✅ 2026-07-08
    
- [x] Kreditkartenabrechnungen (bank-Subtyp) ✅ 2026-07-08
    
- [x] Nebenkostenabrechnungen (housing-Subtyp) ✅ 2026-07-08
    
- [x] Gehaltsabrechnungen ✅ 2026-07-01
    
- [x] Renteninformationen (pension-Subtyp pension_information) ✅ 2026-07-08
    
- [x] Depotauszüge (bank-Subtyp depotuebersicht) ✅ 2026-07-08
    
- [ ] Bescheide
    
- [ ] Energieverträge
    
- [ ] Telekommunikationsrechnungen
    

---

## Dokumentenverwaltung

### Hoch

- [x] Notizen vollständig integrieren
    
- [x] Notizen unabhängig von Freigaben speichern
    
- [x] Dokument erneut analysieren („Erneut prüfen": Klassifikation/Extraktion auf gespeichertem Text wiederholen, Freigabe-Widerruf) ✅ 2026-07-15
    
- [ ] Änderungsdatum (`updated_at`) speichern
    
- [ ] Dokument löschen vollständig testen
    

### Mittel

- [x] Papierkorb statt endgültigem Löschen
    
- [x] Dokument wiederherstellen (Papierkorb → Inbox) ✅ 2026-07-15
    
- [x] Aussteller-Alias-Datei im App-Home ✅ 2026-07-25 (Stufe 2 zur Bulk-Aktion „Aussteller vereinheitlichen"): nutzerpflegbare `config/aussteller_aliase.yaml` (kanonischer Name → Schreibweisen, `*` = Präfix; Änderungen wirken ohne Neustart) ersetzt die hartkodierte KNOWN_ISSUERS-Liste — NEUE Importe und „Erneut prüfen" bekommen direkt den kanonischen Namen (Dateiname UND gespeicherte Felder issuer/employer/insurer); Pflege im Einstellungs-Tab „Aliase" (Editor mit Validierung) oder extern; zugleich Datenschutz-Fix: persönliche Anbieternamen raus aus dem öffentlichen Code (Datei gitignored)
    
- [ ] Dokumente zusammenführen
    
- [ ] Dokumente manuell verschieben
    
- [x] Dokumente manuell umklassifizieren
    

### Niedrig

- [ ] Tags für Dokumente
    
- [ ] Favoriten markieren
    
- [ ] Eigene Kategorien anlegen
    

---

## Suche & Wissensbasis

### Hoch

- [x] Suche in `document_text` ✅ 2026-07-08
    
- [x] Suche in Notizen ✅ 2026-07-08
    
- [x] Suche nach Vertragsnummern (über Volltext in `extracted_data`) ✅ 2026-07-08
    
- [x] SQLite FTS5 statt `LIKE` für die Volltextsuche (Trigram-Substring + bm25-Ranking, Schema v2) ✅ 2026-07-17
    
- [ ] Suche nach Beträgen
    
- [ ] Suche nach Datumsbereichen
    

### Mittel

- [ ] KI-Fragen über Dokumente
    
- [ ] Dokumentzusammenfassungen
    
- [x] Dublettenerkennung (Inhalts-Hash vor OCR/LLM, Dublette → Papierkorb) ✅ 2026-07-15
    
- [x] **Inhaltliche Dubletten-Warnung** ✅ 2026-07-31 — der Inhalts-Hash
  erkennt nur byte-gleiche Dateien; derselbe Beleg ein zweites Mal
  eingescannt lag bisher unbemerkt doppelt im Bestand.
  `src/services/duplicate_service.py` vergleicht stattdessen die erkannten
  Werte (gleicher Aussteller + gleiche Rechnungsnummer ODER gleicher Betrag
  und gleiches Datum; leere Werte matchen nie). Hinweis mit Link im
  Prüf-Workflow, kein Auto-Löschen. Nächster Schritt: der Hinweis soll auch
  die ABWEICHENDEN Felder nennen (siehe Datenqualität → Später)
    
- [ ] Ähnliche Dokumente finden
    

### Später

- [ ] Chat mit Dokumentenbestand
    
- [ ] Dokumentenübergreifende Analysen
    

---

## Steuerfunktionen

### Hoch

- [x] Steuerrelevante Dokumente kennzeichnen (Absetzbarkeit je Dokument: ja/nein/unklar) ✅ 2026-07-08
    
- [x] Steuerrelevante Informationen extrahieren (Beiträge) ✅ 2026-07-01
    
- [x] Steuerjahr automatisch erkennen (`tax_year`-Spalte, steuert Archivpfad) ✅ 2026-07-08
    
- [x] Steuerübersicht pro Jahr ✅ 2026-07-01
    

### Mittel

- [x] Vorsorgeaufwendungen sammeln ✅ 2026-07-01
    
- [x] Versicherungsbeiträge sammeln ✅ 2026-07-01
    
- [x] Werbungskosten sammeln — belegbasiert über tax_purpose-Kennzeichnung; angabenbasierte Pauschalen bewusst out of scope ✅ 2026-07-18
    
- [x] Gesundheitskosten sammeln — Krankheitskosten-Belege über tax_purpose (Anlage agB) ✅ 2026-07-18
    

### Später

- [x] ELSTER-Zuordnung: Summen konkreten Anlagen zuordnen (Anlage N, Vorsorgeaufwand, KAP, agB, § 35a — Ampel + Beleg-Herleitung, tax_check-Golden-Master) ✅ 2026-07-19; offen nur die formale Abnahme eines echten Jahres (dann fällt das „im Aufbau"-Banner)
    
- [ ] ELSTER-Export vorbereiten
    
- [ ] Steuerbericht erzeugen
    
- [x] Grafische Auswertung von Zielwerten — erste Ausbaustufe Jahreseinkommen ✅ 2026-07-25: Analyse-Seite (`/analyse`, Tabs Steuer/Einkommen; `/steuer` leitet um) mit Liniendiagramm Brutto/Steuern/rechnerisches Netto über die Jahre aus den geprüften Lohnsteuerbescheinigungen (framework-freier `income_service`, SVG ohne Chart-Bibliothek); später weitere Zielwerte (z. B. Vorsorge-Summen, § 35a)
    
- [ ] Steuercheckliste pro Jahr / Jahres-Abschluss-Checkliste („für 2025 fehlt: …" aus Vorjahresbestand)
    

---

## Datenqualität

### Hoch

- [x] Automatische Tests erweitern (241 Tests inkl. Fehlerpfade, Whitelists, Frontend-Smoke) ✅ 2026-07-15
    
- [ ] Regressionstests für Dokumenttypen
    
- [ ] **Zweiter Testdatensatz mit fremden Anbietern** — Voraussetzung für weitere Extraktions-Optimierung (evaluate.py misst nur den eigenen Bestand, siehe HANDOVER)
    
- [ ] Testdokumente sammeln
    
- [ ] Fehlerhafte Dokumente kennzeichnen
    
### Mittel

- [x] Statistiken zur Erkennungsqualität (Report auf stdout + `exports/evaluation_report.json`) ✅ 2026-07-08
    
- [ ] Dashboard für Erkennungsfehler
    
- [x] Qualitätskennzahlen pro Dokumenttyp (im Evaluationsreport) ✅ 2026-07-08


### Später

- [ ] Dubletten-Hinweis quittieren („keine Dublette"): ein geprüftes Paar dauerhaft aus der inhaltlichen Dubletten-Warnung nehmen, damit ein erklärter Fehlalarm nicht bei jedem Öffnen erneut erscheint. **Geringe Priorität** — vorher die billigere Maßnahme: der Hinweis soll auch die ABWEICHENDEN Felder nennen, dann ist ein Fehlalarm in Sekunden erkennbar und braucht keinen gespeicherten Vermerk. Offene Fragen für den Bau: Speicherung paarweise (nicht pro Dokument), und der Vermerk muss an die verglichenen Werte gebunden sein und verfallen, sobald sie sich ändern — sonst versteckt er später eine echte Dublette. Bricht die bewusste Zustandslosigkeit von `duplicate_service` (Live-Berechnung).
    
- [ ] Konfidenz-gesteuertes Prüfen: sichere Dokumente automatisch freigeben, nur unsichere vorlegen. **Zurückgestellt (17.07.2026): vorerst prüft der Nutzer alles.** Design-Skizze für später: Kriterium = Regel-Klassifikation + vollständige Pflichtfelder + plausibles Datum; neue Spalten `classification_source` und `verified_source` (user/auto) — Auto-Freigaben dürfen NICHT als Ground Truth für evaluate.py zählen; Opt-in-Schalter, Default aus.
    

---

## Architektur

### Hoch

- [ ] Repository-Struktur aufräumen
    
- [ ] Doppelte Funktionen entfernen
    
- [x] Datenbankzugriffe vereinheitlichen (`open_connection()`-Context-Manager, WAL, timeout) ✅ 2026-07-15
    

### Mittel

- [ ] Änderungsverlauf für Dokumente
    
- [x] Hintergrundjobs für Analyse (Stapel-Import läuft im Hintergrund weiter, `import_job`) ✅ 2026-07-15
    
- [ ] Konfigurierbare Kategorien
    
- [ ] Fristen/Erinnerungen (Kündigungsfristen, Zahlungsziele) aufs Dashboard
    

### Niedrig

- [ ] Plugin-System für neue Dokumenttypen
    
- [ ] API für externe Anwendungen

---

## Installierbarkeit / Packaging (Plan & Details: todo.md)

Entschieden (15.07.2026): Desktop-Einzelplatz, **Linux zuerst**, Windows
später; kein Server, vorerst Single-User. Multinutzer = geteilter
Laptop (getrennte Linux-Konten trennen die Daten bereits; später ggf.
Profil-Umschalter).

Stand: Linux-Paket released (v0.1.0, v0.2.0, v0.2.1 als Tarball + rootloses
`install.sh`). Release-Ablauf und Version-Quelle siehe `docs/07_Betrieb.md`.

- [x] cwd-Entkopplung: App-Home-Konzept (`BUEROKRATOR_HOME` / Dev-Modus / Benutzer-Datenverzeichnis) ✅ 2026-07-15
    
- [x] pypdfium2 statt pdf2image/Poppler (eine native Abhängigkeit weniger) ✅ 2026-07-15
    
- [x] First-Run-Assistent `/einrichtung` (Systemcheck + Install-Hinweise, Speicherorte, Erwartungs-Hinweise) ✅ 2026-07-15
    
- [x] Bundling + Installer (PyInstaller-onedir, Browser-Modus + Beenden-Button, Tarball + rootloses install.sh mit .desktop-Eintrag; AppImage/.deb zurückgestellt) ✅ 2026-07-16
    
- [x] CHANGELOG + Release-Ablauf etabliert; Version nur noch in `src/__init__.py`, der Build liest sie von dort ✅ 2026-07-25
    
- [x] Zweitstart öffnet die laufende Instanz statt am belegten Port zu scheitern; Menüeintrag mit absolutem Icon-Pfad ✅ 2026-07-25 (v0.2.1)
    
- [ ] **Windows-Paket** (erklärtes Ziel): braucht eine Windows-Maschine/VM — PyInstaller kann nicht cross-kompilieren. Offen: `build_windows.ps1` (Zip + Startmenü-Verknüpfung), Windows-Zweig der Spec, Windows-Hinweise im First-Run. Vorarbeit steht (App-Home kennt `%APPDATA%`, Tesseract-Pfad konfigurierbar, keine nativen Extra-Abhängigkeiten)
    
- [ ] Code-Signing (SmartScreen) — erst mit dem Windows-Paket, Zertifikat kostet Geld
    
- [ ] Ollama-Entscheidung: geführte Installation vs. eingebettetes llama.cpp — wird mit dem Windows-Paket drängender (manuelle Installation ist dort eine höhere Hürde)
    
- [x] Flankierend vor Weitergabe: `PRAGMA user_version` + Auto-Backup vor Migration ✅, Update-Weg entschieden (kein Update-Check, [012 Kein Update-Check](docs/decisions/012_kein_update_check.md)) ✅, Hardware-Erwartung im First-Run ✅ 2026-07-16
    
- [ ] Optional: verschlüsselte Backups (age/gpg) — gegen Offline-/Einfachheits-Anspruch abwägen
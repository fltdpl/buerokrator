# Projekt-Roadmap

## Phase 1 - Dokumenteingang

- [x] Projektstruktur erstellen ✅ 2026-06-02
    
- [x] Git Repository anlegen ✅ 2026-06-02
    
- [x] Folder Watcher implementieren ✅ 2026-06-02
    
- [x] Logging einführen ✅ 2026-06-02
    

## Phase 2 – Dokumentverarbeitung

- [x] Document Processor erstellen ✅ 2026-06-02
    
- [x] Pipeline integrieren ✅ 2026-06-02
    
- [x] Fehlerbehandlung einführen ✅ 2026-06-02
    
- [x] Testdokument verarbeiten ✅ 2026-06-02
    
- [x] Verarbeitung protokollieren ✅ 2026-06-02
    

## Phase 3 – OCR

- [x] Tesseract installieren ✅ 2026-06-04
    
- [x] OCR-Service erstellen ✅ 2026-06-04
    
- [x] Text aus PDFs extrahieren ✅ 2026-06-03
    
- [x] Bild-PDFs erkennen ✅ 2026-06-03
    
- [x] OCR auf Bild-PDFs anwenden ✅ 2026-06-04
     
- [x] Bereits vorhandenen PDF-Text bevorzugen ✅ 2026-06-03
     
- [x] OCR-Ergebnisse protokollieren ✅ 2026-06-04
    
- [x] Testdokumente auswerten ✅ 2026-06-04

## Phase 4 – Dokumentanalyse  
  
- [x] Ollama anbinden
    
- [x] Model integrieren
    
- [x] Klassifikations-Prompt erstellen
    
- [x] JSON-Ausgabe definieren
    
- [x] Erste Dokumentklassifikation testen

## Phase 5 – Ablage

- [x] Dateinamensschema finalisieren
    
- [x] Dateinamen automatisch erzeugen
    
- [x] Zielordner bestimmen
    
- [x] Dokumente verschieben
    
- [x] Archivierung protokollieren

## Phase 6 – Datenbank & Steuerexport

- [x] SQLite integrieren
    
- [x] Dokumentdaten speichern
    
- [x] Archivpfade speichern
    
- [ ] Rentenversicherung erfassen
    
- [ ] Chancenorientierte Rentenversicherung erfassen
    
- [ ] Bausparvertrag erfassen
    
- [x] Jahresübersicht erzeugen ✅ 2026-07-01
    
- [x] CSV-Export
    
- [ ] Excel-Export





## Dokumentenerkennung

### Hoch

- [x] Volltextsuche über OCR-Inhalte (`document_text`)
    
- [ ] Suchergebnisse nach Relevanz sortieren
    
- [ ] OCR-Text dauerhaft für alle Importwege speichern
    
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
    
- [x] Extraktionsqualität messen (`evaluate.py`, Felder aktuell 82 %) ✅ 2026-07-08
    
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

- [ ] Notizen vollständig integrieren
    
- [ ] Notizen unabhängig von Freigaben speichern
    
- [ ] Änderungsdatum (`updated_at`) speichern
    
- [ ] Dokument löschen vollständig testen
    

### Mittel

- [ ] Papierkorb statt endgültigem Löschen
    
- [ ] Dokument wiederherstellen
    
- [ ] Dokumente zusammenführen
    
- [ ] Dokumente manuell verschieben
    
- [ ] Dokumente manuell umklassifizieren
    

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
    
- [ ] Suche nach Beträgen
    
- [ ] Suche nach Datumsbereichen
    

### Mittel

- [ ] KI-Fragen über Dokumente
    
- [ ] Dokumentzusammenfassungen
    
- [ ] Dublettenerkennung
    
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
    
- [ ] Werbungskosten sammeln
    
- [ ] Gesundheitskosten sammeln
    

### Später

- [ ] ELSTER-Export vorbereiten
    
- [ ] Steuerbericht erzeugen
    
- [ ] Steuercheckliste pro Jahr
    

---

## Datenqualität

### Hoch

- [ ] Automatische Tests erweitern
    
- [ ] Regressionstests für Dokumenttypen
    
- [ ] Testdokumente sammeln
    
- [ ] Fehlerhafte Dokumente kennzeichnen
    

### Mittel

- [x] Statistiken zur Erkennungsqualität (Report auf stdout + `exports/evaluation_report.json`) ✅ 2026-07-08
    
- [ ] Dashboard für Erkennungsfehler
    
- [x] Qualitätskennzahlen pro Dokumenttyp (im Evaluationsreport) ✅ 2026-07-08
    

---

## Architektur

### Hoch

- [ ] Repository-Struktur aufräumen
    
- [ ] Doppelte Funktionen entfernen
    
- [ ] Datenbankzugriffe vereinheitlichen
    

### Mittel

- [ ] Änderungsverlauf für Dokumente
    
- [ ] Hintergrundjobs für Analyse
    
- [ ] Konfigurierbare Kategorien
    

### Niedrig

- [ ] Plugin-System für neue Dokumenttypen
    
- [ ] API für externe Anwendungen
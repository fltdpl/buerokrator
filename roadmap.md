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
    
- [ ] Jahresübersicht erzeugen
    
- [x] CSV-Export
    
- [ ] Excel-Export





## Dokumentenerkennung

### Hoch

- [ ] Volltextsuche über OCR-Inhalte (`document_text`)
    
- [ ] Suchergebnisse nach Relevanz sortieren
    
- [ ] OCR-Text dauerhaft für alle Importwege speichern
    
- [ ] OCR-Qualität bei Scans verbessern
    
- [ ] Erkennung von mehrseitigen Dokumenten testen
    
- [ ] Fehlerhafte OCR-Ergebnisse protokollieren
    

### Dokumentklassifikation

- [ ] Klassifikationsgenauigkeit messen
    
- [ ] Testdatensatz mit echten Dokumenten aufbauen
    
- [ ] Klassifikation "unknown" analysieren
    
- [ ] Regelbasierte Erkennung vor LLM-Klassifikation prüfen
    
- [ ] Konfidenzscore für Dokumenttyp speichern
    

### Datenextraktion

- [ ] Fehlende Felder erkennen und markieren
    
- [ ] Extraktionsqualität messen
    
- [ ] Validierung von Datumsangaben
    
- [ ] Validierung von Beträgen
    
- [ ] Validierung von Vertragsnummern
    
- [ ] Validierung von Versicherungsnummern
    

### Neue Dokumenttypen

- [ ] Kontoauszüge
    
- [ ] Kreditkartenabrechnungen
    
- [ ] Nebenkostenabrechnungen
    
- [ ] Gehaltsabrechnungen
    
- [ ] Renteninformationen
    
- [ ] Depotauszüge
    
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

- [ ] Suche in `document_text`
    
- [ ] Suche in Notizen
    
- [ ] Suche nach Vertragsnummern
    
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

- [ ] Steuerrelevante Dokumente kennzeichnen
    
- [ ] Steuerrelevante Informationen extrahieren
    
- [ ] Steuerjahr automatisch erkennen
    
- [ ] Steuerübersicht pro Jahr
    

### Mittel

- [ ] Vorsorgeaufwendungen sammeln
    
- [ ] Versicherungsbeiträge sammeln
    
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

- [ ] Statistiken zur Erkennungsqualität
    
- [ ] Dashboard für Erkennungsfehler
    
- [ ] Qualitätskennzahlen pro Dokumenttyp
    

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
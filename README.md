 
# Buerokrator

## Vision

Buerokrator automatisiert die private Dokumentenablage und unterstützt bei der Vorbereitung der jährlichen Steuererklärung.

Das System überwacht einen Eingangsordner, analysiert neue Dokumente, benennt diese automatisch um, archiviert sie an der richtigen Stelle und speichert relevante Informationen in einer Datenbank.

## Hauptfunktionen

- Überwachung eines Scan-Ordners
- OCR für Bild- und PDF-Dokumente
- Dokumentklassifikation
- Automatische Umbenennung
- Automatische Archivierung
- Extraktion steuerrelevanter Informationen
- Lernfähige Dokumenterkennung
- Steuerexport nach Jahren
- Vollständiger lokaler Betrieb

## Projektstatus

Aktuelle Phase: OCR und Bilddatenverarbeitung

## Dokumentation

- [[00_Vision]]
- [[01_Architektur]]
- [[02_Datenmodell]]
- [[03_Dokumenttypen]]
- [[04_Lernsystem]]
- [[05_Steuerlogik]]
- [[06_Ordnerstruktur]]
- [[07_API]]
- [[08_Betrieb]]
- [[09_Decisions]]

## Roadmap

[[roadmap]]


## Externe Abhängigkeiten  
  
### Tesseract OCR  
  
Pfad:  
  
C:\Program Files\Tesseract-OCR  
  
Benötigte Sprachen:  
  
- deu  
- eng  
  
### Poppler  
  
Wird für die Umwandlung von PDF-Seiten in Bilder verwendet.  
  
Benötigt für OCR von gescannten PDFs.
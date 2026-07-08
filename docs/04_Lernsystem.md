# Lernsystem

> **Status: Konzept, nicht umgesetzt.** Es gibt weder Code noch die geplante
> Tabelle `learning_rules`. Was heute existiert und dem Ziel am nächsten
> kommt: Benutzerkorrekturen aus dem Prüf-Workflow sind die Ground Truth der
> Qualitätsmessung (`evaluate.py`) — Verbesserungen fließen manuell in
> Prompts und Regel-Klassifikator zurück, nicht automatisch.

## Ziel

Das System soll aus Benutzerkorrekturen lernen.

## Beispiel

Vorschlag:

Kategorie = Gesundheit

Benutzer:

Kategorie = Versicherung

Regel speichern:

"Zusatzversicherung" → Versicherung

## Lernquellen

- Dateinamen
- Absender
- Dokumenttyp
- Benutzerfeedback

## Finanzprodukte  
  
Das System unterscheidet:  
  
- kurzfristige steuerliche Relevanz  
- langfristige Vermögensbindung  
- reine Informationsdokumente (z. B. Vertragsübersichten)  
  
Beispiele:  
- Rentenversicherung → Vorsorge  
- Bausparvertrag → Vorsorge
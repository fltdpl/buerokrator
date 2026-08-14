from nicegui import ui

from src.frontend.layout import card, page_layout

_INTRO = """
**Buerokrator** legt deine privaten Dokumente automatisch ab und bereitet die
Steuererklärung vor. Alles läuft lokal auf deinem Rechner — keine Cloud, keine
Übertragung an Dritte.
"""

_WORKFLOW = """
### So arbeitest du damit

1. **Importieren** — Lege Dokumente (PDF, PNG, JPG) über *Import* ab oder kopiere
   sie in den `inbox`-Ordner und starte den Stapel-Import. Jede Datei wird per
   OCR gelesen, klassifiziert, umbenannt und nach `archive/<Jahr>/<Kategorie>/`
   einsortiert. Dubletten werden vor der Verarbeitung erkannt und übersprungen.
2. **Prüfen** — Unter *Dokumente* öffnest du einen Eintrag. Links das Formular,
   rechts das PDF bzw. der erkannte Text. Korrigiere die Felder und gib das
   Dokument frei. Rote Felder sind Pflichtfelder, „nicht erkannt" markiert
   Lücken (blockiert nichts).
3. **Auswerten** — Unter *Analyse* liegen zwei Reiter: „Steuer" mit den
   Werten je ELSTER-Anlage (nur aus geprüften Dokumenten, mit
   Beleg-Herleitung und CSV-Export) und „Einkommen" mit dem
   Jahresverlauf.
4. **Sichern** — Unter *Einstellungen → Backup* schreibst du auf Knopfdruck
   Datenbank und Archiv als ZIP-Datei an den konfigurierten Ort. Dort liegt
   auch die **Wiederherstellung**: sie spielt eine Sicherung zurück und legt
   den bisherigen Stand daneben ab, statt ihn zu löschen.
"""

_ARCHIVPFADE = """
### Wenn ein PDF „nicht gefunden" ist

Jedes Dokument merkt sich, wo seine Datei liegt. Spielst du eine Sicherung an
einem **anderen Ort** ein — etwa in eine neu installierte App —, liegen die
Dateien zwar richtig im Archiv, aber die gemerkten Orte zeigen noch dorthin,
wo der Bestand zur Sicherungszeit lag. In der Detailansicht stimmen dann alle
Werte, nur die Vorschau meldet „PDF-Datei nicht gefunden".

Unter *Einstellungen → Datenbank → Archivpfade* steht, wie viele Dokumente
betroffen sind; ein Knopf bindet sie neu an. Vorher entsteht eine Sicherung
der Datenbank, und geändert wird nur, wo die Datei tatsächlich gefunden
wurde — geraten wird nie. Findet sich eine Datei nirgends, bleibt der Eintrag
unangetastet und wird gemeldet.
"""

_TAGS = """
### Tags: was quer zu den Kategorien gehört

Jedes Dokument bekommt genau **eine** Kategorie — der Befund gehört zu
Gesundheit, die Rechnung dazu zu Rechnungen. Was beide verbindet, tragen
**Tags**: frei vergebene Stichwörter wie „Umzug 2026", „Autokauf" oder
„Heizungstausch".

- **Vergeben** beim Prüfen über **＋ Tag**, oder in der Dokumentenliste für
  eine ganze Auswahl auf einmal.
- **Wiederfinden**: ein Klick auf ein Tag in der Liste filtert danach, ein
  zweites Tag engt weiter ein. Die Volltextsuche findet Tags ebenfalls.
- **Aufräumen** unter *Einstellungen → Tags*: umbenennen, zusammenführen
  („Umzug 2026" und „Umzug-2026"), Farbe ändern, löschen.

Keine Systematik nötig: Groß- und Kleinschreibung wird beim Vergleich
ignoriert, und Dokumente ohne Tags bleiben, wie sie sind.
"""

_PROFILE = """
### Mehrere Personen

Unter *Einstellungen → Profile* lässt sich eine zweite Person aufnehmen. Jede
bekommt einen **vollständig getrennten Bestand** — eigene Dokumente, eigenes
Archiv, eigene Steuersummen. Die Einstellungen gelten für alle gemeinsam.
Wessen Unterlagen gerade offen sind, steht in der Seitenleiste.
"""

_SHORTCUTS = """
### Tastenkürzel im Prüf-Workflow

- **Strg + Enter** — Speichern, freigeben und zum nächsten ungeprüften Dokument
- **Esc** — zurück zur Liste
"""

_TRASH = """
### Löschen & Papierkorb

Löschen verschiebt das Original in den Papierkorb (`trash/`), es wird nie sofort
vernichtet. Unter *Einstellungen → Papierkorb* kannst du wiederherstellen (die
Datei landet zurück in der Inbox) oder den Papierkorb endgültig leeren.
"""

_REQUIREMENTS = """
### Voraussetzungen

Buerokrator nutzt lokale Werkzeuge. Ob sie verfügbar sind, zeigt
*Einstellungen → Konfiguration → Systemstatus*:

- **Ollama** mit dem konfigurierten Sprachmodell (Klassifikation & Extraktion)
- **Tesseract OCR** inkl. der Sprachpakete `deu` und `eng`
- **PDF-Renderer pypdfium2** (wandelt gescannte PDF-Seiten in Bilder für die
  OCR; wird als Python-Paket mitinstalliert)
"""


@ui.page("/anleitung")
def help_page():
    with page_layout("Anleitung"):
        ui.label("Anleitung").classes("text-3xl page-title")

        with card("w-full"):
            for block in (
                _INTRO,
                _WORKFLOW,
                _TAGS,
                _PROFILE,
                _SHORTCUTS,
                _TRASH,
                _ARCHIVPFADE,
                _REQUIREMENTS,
            ):
                ui.markdown(block)

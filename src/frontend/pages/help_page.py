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
3. **Steuer** — Unter *Steuer* siehst du je Jahr die Summen nach Kategorie,
   getrennt nach geprüft/ungeprüft, mit CSV-Export.
4. **Sichern** — Unter *Einstellungen → Backup* schreibst du auf Knopfdruck
   Datenbank und Archiv als ZIP-Datei an den konfigurierten Ort.
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
- **Poppler** (wandelt gescannte PDF-Seiten in Bilder für die OCR)
"""


@ui.page("/anleitung")
def help_page():
    with page_layout("Anleitung"):
        ui.label("Anleitung").classes("text-3xl page-title")

        with card("w-full"):
            for block in (_INTRO, _WORKFLOW, _SHORTCUTS, _TRASH, _REQUIREMENTS):
                ui.markdown(block)

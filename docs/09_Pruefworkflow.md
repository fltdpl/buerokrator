# Prüfworkflow

Der Import liefert einen Vorschlag, keine Wahrheit. Erst die Freigabe
(`verified = 1`) macht daraus einen belastbaren Datensatz — an ihr hängen die
[Steuersummen](04_Steuerlogik.md), das Aussteller-Gedächtnis und die
Qualitätsmessung. Sie ist deshalb immer eine bewusste Handlung, nie ein
Nebeneffekt.

## Zustände

```mermaid
stateDiagram-v2
    direction LR
    Ungeprueft: 🟡 ungeprüft
    Geprueft: 🟢 geprüft
    Papierkorb: 🗑 Papierkorb

    [*] --> Ungeprueft: Import
    Ungeprueft --> Ungeprueft: Speichern
    Ungeprueft --> Geprueft: Freigeben
    Geprueft --> Geprueft: Speichern
    Geprueft --> Ungeprueft: Widerrufen
    Geprueft --> Ungeprueft: Erneut prüfen
    Geprueft --> Ungeprueft: Bulk-Änderung
    Ungeprueft --> Papierkorb: Löschen
    Geprueft --> Papierkorb: Löschen
    Papierkorb --> Ungeprueft: Wiederherstellen
```

„💾 Speichern" lässt den Status, wie er ist, „✅ Speichern & Freigeben" setzt
ihn und springt weiter; geschrieben wird das Flag nur in
`set_document_verified.py`. „Erneut prüfen" verwirft zusätzlich den
Steuerrelevanz-Override. Der Papierkorb ist kein Flag: die Zeile ist weg, die
Datei liegt in `trash/`.

## Ablauf auf der Prüfseite

```mermaid
flowchart TD
    E["Einstieg: Dashboard, Import, Liste, Blättern"] --> D["Prüfseite öffnen"]
    D --> H["Hinweise lesen: mögliche Dublette, unerwarteter Typ"]
    H --> T["Dokumenttyp und Unterart wählen"]
    T --> F["Felder gegen PDF oder OCR-Text prüfen"]
    F --> S["Steuerrelevanz, Zweck, Notiz"]
    S --> Q{"freigeben?"}
    Q -->|"Speichern und Freigeben"| N["weiter zum nächsten ungeprüften"]
    Q -->|"nur Speichern"| R["Seite neu laden, Status bleibt"]
    R --> F
    F -.- P[/"Hinweis: leere Pflichtfelder werden nur hervorgehoben"/]
    style P fill:#f4f4f4,stroke:#999
```

Die Hinweise stehen bewusst vor der Entscheidung — mögliche Dublette
(`duplicate_service.py`) und unerwarteter Typ (`issuer_memory.py`); beide
ändern nie etwas von selbst. Welche Felder erscheinen, entscheiden Typ **und**
Unterart (`form_schema.py`). Gespeichert wird über `merge_form_values` →
`whitelist_fields` (trimmen, Datum deutsch, Unterart ans Vokabular binden,
fremde Felder verwerfen) → `enforce_amount_signs` → `rename_document` →
`update_document`.

## Bewusst nicht

- **Speichern gibt nicht frei** — sonst zählen halb geprüfte Werte mit.
- **Pflichtfelder blockieren nicht**, ein unleserlicher Scan darf nicht am
  Speichern hindern.
- **Hinweise korrigieren nichts automatisch**, gelöscht wird nur in den
  Papierkorb.
- **Umbenannt wird nur beim Speichern** — nicht bei Bulk-Aktionen oder
  „Erneut prüfen".

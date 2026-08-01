# Entscheidung 010

## Thema

NiceGUI statt Streamlit als Oberfläche

Ersetzt [003 Streamlit](003_streamlit.md).

## Begründung

- Echtes Event-Modell statt Komplett-Rerun: Tastatur-Shortcuts
  (Strg+Enter im Prüf-Workflow), persistenter PDF-Viewer, schnellere
  Bedienung.
- Bleibt reines Python; die Service-Schicht (`src/services`) trennt
  Frontend und Logik sauber.
- PDFs werden direkt aus dem Archiv ausgeliefert (Route `/pdf/<id>`,
  nur localhost) — keine static-Kopien privater Dokumente mehr.
- React + FastAPI wurde verworfen: zweite Toolchain und eigene
  API-Schicht stehen für ein lokales Einzelbenutzer-Tool in keinem
  Verhältnis zum Nutzen.

## Status

Akzeptiert

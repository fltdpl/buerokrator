
# Entscheidung 004

## Thema

Monolithische Python-Anwendung

Buerokrator/
│
├── .gitignore
├── README.md
├── AGENT_CONTEXT.md
├── HANDOVER.md
├── todo.md
├── roadmap.md
├── requirements.txt
├── app.py            (Streamlit-Einstieg / Dashboard)
├── main.py           (Live-Watcher, Alt-Weg)
├── evaluate.py       (Qualitätsmessung)
│
├── config/
│ └── settings.yaml
│
├── docs/
│ ├── decisions/
│ └── ...
│
├── pages/            (Streamlit-Multipage-Seiten)
│
├── src/
│ ├── core/           (Dokumenttypen, Feld-Whitelist, Betrags-Utils)
│ ├── ocr/
│ ├── classifier/     (Regeln + LLM, Extraktion, Prompts)
│ ├── organizer/
│ ├── database/
│ ├── gui/
│ ├── tax/
│ ├── evaluation/
│ ├── processor/
│ └── watcher/
│
├── tests/
│
├── inbox/
├── archive/
├── exports/
├── database/
├── static/           (pdf/ = Anzeige-Cache des Viewers)
├── logs/
│
└── examples/

## Begründung

- Einzelplatzsystem
- geringe Komplexität
- lokale Verarbeitung
- einfache Wartung

## Status

Akzeptiert

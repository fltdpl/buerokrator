
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
├── src/
│ ├── core/           (Dokumenttypen, Feld-Whitelist, Betrags-Utils)
│ ├── ocr/
│ ├── classifier/     (Regeln + LLM, Extraktion, Prompts)
│ ├── organizer/
│ ├── database/
│ ├── services/       (framework-freie Anwendungslogik für die GUI)
│ ├── frontend/       (NiceGUI; Start: python -m src.frontend.main)
│ ├── tax/
│ ├── evaluation/
│ ├── processor/
│ └── watcher/
│
├── tests/
│
├── inbox/
├── archive/
├── trash/            (Papierkorb gelöschter Dokumente)
├── exports/
├── database/
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

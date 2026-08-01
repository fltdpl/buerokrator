
# Entscheidung 004

## Thema

Monolithische Python-Anwendung

Buerokrator/
│
├── README.md         (Nutzersicht)
├── AGENT_CONTEXT.md  (Regeln und Konventionen für Agenten)
├── CHANGELOG.md      (Änderungen je Release)
├── roadmap.md        (Langfrist-Sicht)
├── requirements.txt
├── main.py           (startet die App; = python -m src.frontend.main)
│
├── config/
│ └── settings.yaml
│
├── tools/            (CLI-Werkzeuge, nicht Teil der App)
│ ├── evaluate.py     (Qualitätsmessung)
│ └── tax_check.py    (Golden-Master-Abgleich Steuer)
│
├── docs/
│ ├── decisions/      (ADRs)
│ └── screenshots/
│
├── src/
│ ├── core/           (Dokumenttypen, Feld-Whitelist, App-Home, Betrags-Utils)
│ ├── ocr/            (layouttreuer PDF-Text, Tesseract für Scans)
│ ├── classifier/     (Regeln + LLM, Extraktion, Prompts)
│ ├── extraction/     (deterministische Regelparser für amtliche Formulare)
│ ├── organizer/      (Dateinamen-Bau, Archivierung, Aussteller-Aliase)
│ ├── database/
│ ├── services/       (framework-freie Anwendungslogik für die GUI)
│ ├── frontend/       (NiceGUI; Start: python -m src.frontend.main)
│ ├── tax/
│ ├── evaluation/
│ └── processor/
│
├── tests/
├── packaging/        (PyInstaller-Spec, build_linux.sh, install.sh)
├── assets/           (Logo, Icons)
│
└── Datenordner (gitignored, hängen am App-Home)
  inbox/ · archive/ · trash/ · exports/ · database/ · logs/ · backups/

## Begründung

- Einzelplatzsystem
- geringe Komplexität
- lokale Verarbeitung
- einfache Wartung

## Status

Akzeptiert

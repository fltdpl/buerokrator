# Entscheidung 007

## Thema

Modellwechsel von qwen3:1.7b auf gemma3:4b

Ersetzt die Modellwahl aus [[002_ollama]] (die Grundsatzentscheidung für
Ollama bleibt bestehen).

## Begründung

- Bessere Klassifikations- und Extraktionsqualität, messbar mit
  `evaluate.py` gegen die geprüften Dokumente
- Laufzeit auf der aktuellen Hardware akzeptabel
- Modell bleibt über `config/settings.yaml` austauschbar

## Status

Akzeptiert

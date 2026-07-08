# Entscheidung 008

## Thema

Regel-Klassifikation vor dem LLM

Vor dem LLM-Aufruf prüft ein Keyword-Scoring (`src/classifier/rule_classifier.py`),
ob der Dokumenttyp eindeutig ist: Gewichte Titel 3 / Indiz 2 / schwach 1,
Treffer im ersten Textdrittel zählen doppelt. Die Regel entscheidet nur bei
Score ≥ 3, Vorsprung ≥ 2 und mindestens einem Treffer mit Gewicht ≥ 2 —
sonst entscheidet das LLM. Jede Klassifikation liefert ihre Quelle mit
(`source` = rule/llm), auch im Evaluationsreport getrennt ausgewiesen.

## Begründung

- Deterministisch und nachvollziehbar für eindeutige Dokumente
- Deutlich schneller als ein LLM-Aufruf
- Konservative Schwellen: im Zweifel entscheidet das LLM, damit Regeln
  keine schwierigen Fälle falsch abräumen

## Status

Akzeptiert

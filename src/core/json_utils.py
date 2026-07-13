import json
import re


def parse_llm_json(content):
    """Parst die JSON-Antwort eines LLM (robust gegen typische Verpackungen).

    Entfernt Markdown-Codezäune; scheitert das direkte Parsen, wird der
    erste {...}-Block herausgeschnitten und erneut versucht — kleine Modelle
    packen gelegentlich Prosa um ihr JSON ("Hier ist das Ergebnis: {...}").
    Wirft weiterhin, wenn auch das kein gültiges JSON ist (der Aufrufer hat
    dafür einen Retry).
    """
    content = (
        content
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        return json.loads(content)

    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)

        if match:
            return json.loads(match.group(0))

        raise

from ollama import chat

from src.classifier.prompt_loader import load_prompt
from src.classifier.rule_classifier import match_rule
from src.core.config import load_config
from src.core.document_types import DOCUMENT_TYPE_SET, UNKNOWN
from src.core.json_utils import parse_llm_json
from src.core.logger import logger


def classify(text):
    # Regelbasierte Vorprüfung: eindeutige Schlüsselwörter (z. B.
    # "Lohnsteuerbescheinigung") werden deterministisch erkannt, ohne das LLM
    # zu bemühen.
    rule_type = match_rule(text)
    if rule_type is not None:
        logger.info(f"Regel-Treffer: {rule_type}")
        return {"document_type": rule_type, "source": "rule"}

    config = load_config()
    model = config["classifier"]["model"]
    max_input_chars = config["classifier"]["max_input_chars"]
    temperature = config["classifier"]["temperature"]
    prompt = load_prompt("classify.txt")
    prompt = prompt.format(document_text=text[:max_input_chars])

    # Ollama ist optional: Ist der Dienst nicht erreichbar, wird das Dokument
    # als "unknown" archiviert (source "none") und im Prüf-Workflow von Hand
    # nachgepflegt, statt den Import scheitern zu lassen.
    try:
        response = chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperature},
        )

    except Exception as e:
        logger.warning(f"Ollama nicht verfügbar — Klassifikation ohne LLM: {e}")

        return {"document_type": UNKNOWN, "source": "none"}

    try:
        result = parse_llm_json(response.message.content)

        document_type = result.get(
            "document_type",
            UNKNOWN,
        )

        if document_type not in DOCUMENT_TYPE_SET:
            logger.warning(f"Ungültiger Dokumenttyp erkannt: {document_type}")

            result["document_type"] = UNKNOWN

        result["source"] = "llm"

        return result

    except Exception as e:
        logger.error(f"JSON Fehler bei der Klassifikation: {e}")

        return {"document_type": UNKNOWN, "source": "llm"}

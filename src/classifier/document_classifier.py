from ollama import chat

from src.classifier.prompt_loader import load_prompt
from src.core.config import load_config
from src.core.json_utils import parse_llm_json

config = load_config()


def classify(text):
    model = config["classifier"]["model"]
    max_input_chars = config["classifier"]["max_input_chars"]
    temperature = config["classifier"]["temperature"]
    prompt = load_prompt("classify.txt")
    prompt = prompt.format(document_text=text[:max_input_chars])

    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )

    try:
        # print("=== RESPONSE ANTWORT ===")
        # print(response.message.content)
        # print("========================")

        result = parse_llm_json(response.message.content)

        ALLOWED_TYPES = {
            "invoice",
            "insurance",
            "pension",
            "tax",
            "bank",
            "housing",
            "unknown",
        }

        document_type = result.get(
            "document_type",
            "unknown",
        )

        if document_type not in ALLOWED_TYPES:
            print(f"Ungültiger Dokumenttyp erkannt: {document_type}")

            result["document_type"] = "unknown"

        return result

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {"document_type": "unknown"}

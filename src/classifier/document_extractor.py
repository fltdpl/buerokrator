from ollama import chat

from src.classifier.prompt_loader import load_prompt
from src.core.config import load_config
from src.core.json_utils import parse_llm_json

config = load_config()


def extract_invoice(text):
    model = config["classifier"]["model"]
    max_input_chars = config["classifier"]["max_input_chars"]
    temperature = config["classifier"]["temperature"]

    prompt = load_prompt("extract_invoice.txt")
    prompt = prompt.format(document_text=text[:max_input_chars])
    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )

    try:
        print("=== EXTRACTOR ANTWORT ===")
        print(response.message.content)
        print("=========================")

        data = parse_llm_json(response.message.content)
        amount = data.get("amount")

        if isinstance(amount, str):
            amount = amount.replace("€", "").replace(",", ".").strip()

            try:
                amount = float(amount)

            except Exception:
                amount = None

            data["amount"] = amount

        return data

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {}


def extract_tax(text):
    model = config["classifier"]["model"]
    max_input_chars = config["classifier"]["max_input_chars"]
    temperature = config["classifier"]["temperature"]

    prompt = load_prompt("extract_tax.txt")
    prompt = prompt.format(document_text=text[:max_input_chars])
    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )

    try:
        print("=== EXTRACTOR ANTWORT ===")
        print(response.message.content)
        print("=========================")

        return parse_llm_json(response.message.content)

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {}


def extract_document(document_type, text):

    if document_type == "invoice":
        return extract_invoice(text)

    if document_type == "tax":
        return extract_tax(text)

    return {}

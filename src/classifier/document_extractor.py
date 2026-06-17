from ollama import chat

from src.classifier.prompt_loader import load_prompt
from src.core.config import load_config
from src.core.json_utils import parse_llm_json

config = load_config()


def run_extractor(prompt_file, text):

    model = config["classifier"]["model"]
    max_input_chars = config["classifier"]["max_input_chars"]
    temperature = config["classifier"]["temperature"]

    prompt = load_prompt(prompt_file)
    prompt = prompt.format(document_text=text[:max_input_chars])

    response = chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        options={
            "temperature": temperature,
        },
    )

    print("=== EXTRACTOR ANTWORT ===")
    print(response.message.content)
    print("=========================")

    return parse_llm_json(response.message.content)


def extract_invoice(text):
    try:
        data = run_extractor(
            "extract_invoice.txt",
            text,
        )

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
    try:
        return run_extractor(
            "extract_tax.txt",
            text,
        )

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {}


def extract_insurance(text):
    try:
        return run_extractor(
            "extract_insurance.txt",
            text,
        )

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {}


def extract_pension(text):
    try:
        return run_extractor(
            "extract_pension.txt",
            text,
        )

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {}


def extract_document(
    document_type,
    text,
):

    if document_type == "invoice":
        return extract_invoice(text)

    if document_type == "tax":
        return extract_tax(text)

    if document_type == "insurance":
        return extract_insurance(text)

    if document_type == "pension":
        return extract_pension(text)

    return {}

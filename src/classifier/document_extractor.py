from ollama import chat

from src.classifier.prompt_loader import load_prompt
from src.core.amount_utils import normalize_amount
from src.core.config import load_config
from src.core.document_types import BANK, HOUSING, INSURANCE, INVOICE, PENSION, TAX
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


def _normalize_amount_field(data):
    if isinstance(data, dict) and "amount" in data:
        data["amount"] = normalize_amount(data.get("amount"))

    return data


def extract_invoice(text):
    try:
        data = run_extractor(
            "extract_invoice.txt",
            text,
        )

        return _normalize_amount_field(data)

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
        data = run_extractor(
            "extract_insurance.txt",
            text,
        )

        return _normalize_amount_field(data)

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {}


def extract_pension(text):
    try:
        data = run_extractor(
            "extract_pension.txt",
            text,
        )

        return _normalize_amount_field(data)

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {}


def extract_bank(text):
    try:
        return run_extractor(
            "extract_bank.txt",
            text,
        )

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {}


def extract_housing(text):
    try:
        return run_extractor(
            "extract_housing.txt",
            text,
        )

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {}


def extract_document(
    document_type,
    text,
):
    extractors = {
        INVOICE: extract_invoice,
        TAX: extract_tax,
        INSURANCE: extract_insurance,
        PENSION: extract_pension,
        BANK: extract_bank,
        HOUSING: extract_housing,
    }

    extractor = extractors.get(document_type)
    if extractor:
        return extractor(text)

    return {}

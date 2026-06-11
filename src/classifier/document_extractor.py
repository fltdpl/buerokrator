from urllib import response

from ollama import chat

from src.core.config import load_config
from src.core.json_utils import parse_llm_json

config = load_config()


def extract_invoice(text):
    model = config["classifier"]["model"]
    max_input_chars = config["classifier"]["max_input_chars"]
    temperature = config["classifier"]["temperature"]
    prompt = f"""
Antworte ausschließlich mit JSON.

Schema:

{{
  "issuer": "",
  "document_date": "",
  "invoice_number": "",
  "amount": null
}}

Extrahiere:

- issuer = Rechnungssteller
- document_date = Rechnungsdatum
- invoice_number = Rechnungsnummer
- amount = Rechnungsbetrag

Wenn ein Wert nicht gefunden wird, verwende "" bzw. null.
Dokument:

{text[:max_input_chars]}
"""

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

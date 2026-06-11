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

- issuer = Rechnungssteller oder Verkäufer

- document_date = Rechnungsdatum

Format:
DD.MM.YYYY

Beispiel:
05.12.2025

- invoice_number = Rechnungsnummer

- amount = Rechnungsbetrag

amount muss eine Zahl sein.

Beispiele:

199.99
60.00
145.80

Keine Währungszeichen.
Keine Anführungszeichen.

Wenn ein Wert nicht gefunden wird,
verwende "" bzw. null.

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

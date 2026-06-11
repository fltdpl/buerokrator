from ollama import chat

from src.core.config import load_config
from src.core.json_utils import parse_llm_json

config = load_config()


def classify(text):
    model = config["classifier"]["model"]
    max_input_chars = config["classifier"]["max_input_chars"]
    temperature = config["classifier"]["temperature"]
    prompt = f"""
Antworte ausschließlich mit JSON.
Schema:
{{
  "document_type": ""
}}

Mögliche document_type Werte:

invoice:
Rechnungen, Arztrechnungen, Handwerkerrechnungen,
Kaufbelege, Zahlungsaufforderungen

insurance:
Versicherungspolicen, Versicherungsverträge,
Versicherungsinformationen

building_savings:
Bausparverträge, Bausparkonten,
Bausparkassen-Mitteilungen

pension:
Renteninformationen,
Rentenbescheide,
Altersvorsorge

tax:
Lohnsteuerbescheinigungen,
Steuerbescheide,
Einkommensteuer,
Finanzamt,
ELSTER,
Steuerunterlagen

unknown:
wenn keine Kategorie passt

Dokument:

{text[:max_input_chars]}
"""

    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )

    try:
        # print("=== RESPONSE ANTWORT ===")
        # print(response.message.content)
        # print("========================")

        return parse_llm_json(response.message.content)

    except Exception as e:
        print(f"JSON Fehler: {e}")

        return {"document_type": "unknown"}

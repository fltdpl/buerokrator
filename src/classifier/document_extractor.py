import json
from urllib import response
from ollama import chat
from src.core.config import load_config


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
  "amount": null
}}

Dokument:

{text[:max_input_chars]}
"""

    response = chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": temperature
        }
    )

    try:
        print("=== EXTRACTOR ANTWORT ===")
        #print(response.message.content)
        #print("=========================")
        
        return json.loads(
            response.message.content
        )

    except Exception as e:
        print(
            f"JSON Fehler: {e}"
        )
        return {}
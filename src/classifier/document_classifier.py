import json
from ollama import chat
from src.core.config import load_config


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

- invoice
- insurance
- building_savings
- pension
- tax
- unknown

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
        #print("=== LLM Antwort ===")
        #print(response.message.content)
        #print("===================")

        return json.loads(
            response.message.content
        )

    except Exception as e:
        print(f"JSON Fehler: {e}")
        return {
            "document_type": "unknown"
        }
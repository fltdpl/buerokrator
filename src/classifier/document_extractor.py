from ollama import chat

from src.classifier.prompt_loader import load_prompt
from src.core.amount_utils import enforce_amount_signs, normalize_amount
from src.core.config import load_config
from src.core.document_fields import whitelist_fields
from src.core.document_types import (
    BANK,
    EMPLOYMENT,
    HOUSING,
    INSURANCE,
    INVOICE,
    LEGAL,
    PENSION,
    TAX,
)
from src.core.json_utils import parse_llm_json
from src.core.logger import logger
from src.extraction.pension_refiner import refine_pension_fields

# Steuer- und Vorsorgedokumente brauchen mehr Kontext: Titel steht oben,
# die Beträge (Lohnsteuer/Soli bzw. Zinsen/Salden beim Bauspar-Jahresauszug)
# stehen oft weiter unten.
TAX_MAX_INPUT_CHARS = 6000
PENSION_MAX_INPUT_CHARS = 6000
EMPLOYMENT_MAX_INPUT_CHARS = 6000


def run_extractor(prompt_file, text, max_input_chars=None):

    config = load_config()

    model = config["classifier"]["model"]
    if max_input_chars is None:
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

    logger.debug(f"Extraktor-Antwort: {response.message.content}")

    return parse_llm_json(response.message.content)


# Felder, die als Betrag normalisiert werden.
AMOUNT_FIELDS = {
    INVOICE: ("amount",),
    INSURANCE: ("amount",),
    HOUSING: ("amount",),
    PENSION: (
        "amount",
        "interest",
        "capital_gains_tax",
        "soli",
        "church_tax",
        "contributions_total",
        "opening_balance",
        "closing_balance",
    ),
    TAX: (
        "gross_amount",
        "income_tax",
        "soli",
        "church_tax",
        "net_amount",
        "settlement_amount",
    ),
    EMPLOYMENT: (
        "gross_amount",
        "income_tax",
        "soli",
        "church_tax",
        "net_amount",
    ),
}

PROMPT_FILES = {
    INVOICE: "extract_invoice.txt",
    TAX: "extract_tax.txt",
    INSURANCE: "extract_insurance.txt",
    PENSION: "extract_pension.txt",
    BANK: "extract_bank.txt",
    HOUSING: "extract_housing.txt",
    EMPLOYMENT: "extract_employment.txt",
    LEGAL: "extract_legal.txt",
}


def _extract(document_type, text, max_input_chars=None):
    # Ein Wiederholungsversuch: das LLM liefert gelegentlich einmalig
    # ungültiges JSON — ohne Retry gehen dann alle Felder verloren.
    data = None
    for attempt in (1, 2):
        try:
            data = run_extractor(
                PROMPT_FILES[document_type],
                text,
                max_input_chars=max_input_chars,
            )
            break

        except Exception as e:
            logger.warning(f"JSON Fehler bei der Extraktion (Versuch {attempt}): {e}")

    if data is None:
        return {}

    if not isinstance(data, dict):
        return {}

    for field in AMOUNT_FIELDS.get(document_type, ()):
        if field in data:
            data[field] = normalize_amount(data.get(field))

    return enforce_amount_signs(whitelist_fields(document_type, data))


def extract_invoice(text):
    return _extract(INVOICE, text)


def extract_tax(text):
    return _extract(TAX, text, max_input_chars=TAX_MAX_INPUT_CHARS)


def extract_insurance(text):
    return _extract(INSURANCE, text)


def extract_pension(text):
    data = _extract(PENSION, text, max_input_chars=PENSION_MAX_INPUT_CHARS)

    # Regelbasierte Korrektur (Salden, Zinsen, Beitragssumme, amtliche
    # Kapitalertragsfelder). Danach erneut whitelisten: der Parser kann den
    # Subtyp setzen und damit andere Felder gültig machen.
    refined = refine_pension_fields(text, data)
    if refined is data:
        return data

    return enforce_amount_signs(whitelist_fields(PENSION, refined))


def extract_bank(text):
    return _extract(BANK, text)


def extract_housing(text):
    return _extract(HOUSING, text)


def extract_legal(text):
    return _extract(LEGAL, text)


def extract_employment(text):
    return _extract(EMPLOYMENT, text, max_input_chars=EMPLOYMENT_MAX_INPUT_CHARS)


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
        EMPLOYMENT: extract_employment,
        LEGAL: extract_legal,
    }

    extractor = extractors.get(document_type)
    if extractor:
        return extractor(text)

    return {}

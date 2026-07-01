from pathlib import Path

from src.core.config import load_config
from src.core.document_types import (
    ARCHIVE_CATEGORY_LABELS,
    DOCUMENT_TYPES,
    DOCUMENT_TYPE_LABELS,
)
from src.organizer.filename_builder import build_filename


def get_prompt_document_types():
    prompt = Path("src/classifier/prompts/classify.txt").read_text(
        encoding="utf-8",
    )
    lines = prompt.splitlines()
    start = lines.index("Wähle exakt einen dieser Werte:") + 2
    end = lines.index("Verwende ausschließlich einen dieser Werte.")

    return tuple(line.strip() for line in lines[start:end] if line.strip())


def test_config_prompt_and_labels_use_the_same_document_types():
    config = load_config()

    assert tuple(config["supported_document_types"]) == DOCUMENT_TYPES
    assert tuple(config["archive"]["category_mapping"]) == DOCUMENT_TYPES
    assert config["archive"]["category_mapping"] == ARCHIVE_CATEGORY_LABELS
    assert set(DOCUMENT_TYPE_LABELS) == set(DOCUMENT_TYPES)
    assert set(ARCHIVE_CATEGORY_LABELS) == set(DOCUMENT_TYPES)
    assert get_prompt_document_types() == DOCUMENT_TYPES


def test_all_document_types_can_build_a_filename():
    extracted_data = {
        "issuer": "Test Issuer",
        "insurer": "Test Insurer",
        "employer": "Test Employer",
        "bank": "Test Bank",
        "landlord": "Test Landlord",
        "document_date": "11.03.2026",
        "invoice_number": "RE/123",
        "amount": 42.5,
        "insurance_type": "Haftpflicht",
        "policy_number": "PN/123.4",
        "tax_year": "2026",
        "document_subtype": "Bescheid",
    }

    for document_type in DOCUMENT_TYPES:
        filename = build_filename(
            {"document_type": document_type},
            extracted_data,
            "scan.pdf",
        )

        assert filename
        assert filename.endswith(".pdf")

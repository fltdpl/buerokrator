import json

import pytest

from src.core.json_utils import parse_llm_json


def test_plain_json():
    assert parse_llm_json('{"a": 1}') == {"a": 1}


def test_markdown_codefence():
    assert parse_llm_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_prose_around_json():
    # Kleine Modelle packen gelegentlich Prosa um ihr JSON.
    content = 'Hier ist das Ergebnis:\n{"issuer": "ACME", "amount": 42}\nViel Erfolg!'

    assert parse_llm_json(content) == {"issuer": "ACME", "amount": 42}


def test_prose_with_codefence_and_nested_braces():
    content = 'Gerne! ```json\n{"a": {"b": 2}}\n``` Das JSON oben ist vollständig.'

    assert parse_llm_json(content) == {"a": {"b": 2}}


def test_invalid_json_still_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_llm_json("kein JSON weit und breit")
